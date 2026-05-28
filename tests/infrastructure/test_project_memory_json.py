from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lattice.config import load_config
from lattice.infrastructure.project_memory_json import (
    FilesystemUnitSource,
    JsonProjectMemoryShapeValidator,
    JsonTypeSource,
    spec_registry_from_project_memory,
)
from lattice.modules.project_memory import (
    ProjectMemory,
    ProjectMemoryTypes,
    ProjectMemoryUnit,
    RawProjectMemoryUnit,
    SourceLocation,
)
from lattice.registry import load_registry, load_type_registry


class ProjectMemoryJsonAdapterTests(unittest.TestCase):
    def test_filesystem_unit_source_loads_json_units_and_read_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs_dir = root / ".lattice/specs/examples"
            specs_dir.mkdir(parents=True)
            (specs_dir / "UNIT-001.json").write_text(
                json.dumps(
                    {
                        "id": "UNIT-001",
                        "kind": "domain_object",
                        "name": "Unit",
                        "owner": "tests",
                        "status": "active",
                        "description": "Unit.",
                    }
                ),
                encoding="utf-8",
            )
            (specs_dir / "bad.json").write_text("{", encoding="utf-8")

            result = FilesystemUnitSource(load_config(root)).read_units()

            self.assertEqual(["UNIT-001"], [unit.data["id"] for unit in result.units])
            self.assertTrue(
                any(issue.code == "LATTICE-JSON-001" for issue in result.issues)
            )

    def test_json_type_source_loads_registry_schema_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_dir = root / ".lattice/registry"
            schema_dir = root / ".lattice/schemas"
            registry_dir.mkdir(parents=True)
            schema_dir.mkdir(parents=True)
            (schema_dir / "custom.schema.json").write_text(
                json.dumps({"type": "object", "required": ["custom"]}),
                encoding="utf-8",
            )
            (registry_dir / "spec-types.json").write_text(
                json.dumps(
                    {
                        "custom": {
                            "extends": "knowledge_unit",
                            "schema_path": ".lattice/schemas/custom.schema.json",
                            "required": ["id", "kind", "name", "custom"],
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = JsonTypeSource(load_config(root)).read_types()

            self.assertEqual((), result.issues)
            self.assertIn("custom", result.types.definitions)
            self.assertEqual(
                ".lattice/schemas/custom.schema.json",
                result.types.definitions["custom"].schema_path,
            )
            self.assertEqual(
                {"type": "object", "required": ["custom"]},
                result.types.definitions["custom"].schema,
            )

    def test_json_project_memory_shape_validator_reports_schema_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = load_config(root)
            type_result = JsonTypeSource(config).read_types()
            raw = RawProjectMemoryUnit(
                {
                    "id": "ENUM-001",
                    "kind": "enum",
                    "name": "Enum",
                    "owner": "tests",
                    "status": "active",
                    "description": "Enum.",
                },
                SourceLocation(label="memory:ENUM-001"),
            )

            issues = JsonProjectMemoryShapeValidator().validate(raw, type_result.types)

            self.assertTrue(
                any(
                    issue.code == "LATTICE-SCHEMA-006"
                    and "enum schema" in issue.message
                    and "values" in issue.message
                    for issue in issues
                )
            )

    def test_load_type_registry_preserves_semantic_type_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_dir = root / ".lattice/registry"
            registry_dir.mkdir(parents=True)
            (registry_dir / "spec-types.json").write_text(
                json.dumps(
                    {
                        "bad_child": {
                            "extends": "missing_parent",
                            "required": ["id", "kind", "name"],
                        },
                        "bad_constraint": {
                            "extends": "knowledge_unit",
                            "reference_fields": ["references"],
                            "reference_tag_constraints": {
                                "not_a_reference": {
                                    "type": "missing_tag",
                                    "value": "anything",
                                }
                            },
                        },
                        "bad_tag_value": {
                            "extends": "knowledge_unit",
                            "reference_fields": ["references"],
                            "reference_tag_constraints": {
                                "references": {
                                    "type": "EntityType",
                                    "value": "MissingValue",
                                }
                            },
                        },
                        "tag_types": {"EntityType": {"values": ["BusinessEntity"]}},
                    }
                ),
                encoding="utf-8",
            )

            _, _, issues = load_type_registry(load_config(root))
            codes = {issue.code for issue in issues}

            self.assertIn("LATTICE-TYPE-004", codes)
            self.assertIn("LATTICE-TYPE-010", codes)
            self.assertIn("LATTICE-TAG-001", codes)
            self.assertIn("LATTICE-TAG-002", codes)

    def test_load_type_registry_reports_type_hierarchy_cycles_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_dir = root / ".lattice/registry"
            registry_dir.mkdir(parents=True)
            (registry_dir / "spec-types.json").write_text(
                json.dumps(
                    {
                        "cycle_a": {"extends": "cycle_b"},
                        "cycle_b": {"extends": "cycle_a"},
                    }
                ),
                encoding="utf-8",
            )

            _, _, issues = load_type_registry(load_config(root))
            cycle_issues = [
                issue for issue in issues if issue.code == "LATTICE-TYPE-011"
            ]

            self.assertEqual(1, len(cycle_issues))
            self.assertIn("cycle", cycle_issues[0].message)

    def test_load_registry_reports_major_graph_and_shape_issue_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs_dir = root / ".lattice/specs/examples"
            specs_dir.mkdir(parents=True)
            unit = {
                "id": "UNIT-001",
                "kind": "domain_object",
                "name": "Unit",
                "owner": "tests",
                "status": "active",
                "description": "Unit.",
                "references": ["MISSING-001"],
            }
            (specs_dir / "a.json").write_text(json.dumps(unit), encoding="utf-8")
            (specs_dir / "b.json").write_text(json.dumps(unit), encoding="utf-8")

            registry = load_registry(load_config(root))
            codes = {issue.code for issue in registry.issues}

            self.assertIn("LATTICE-ID-001", codes)
            self.assertIn("LATTICE-REF-001", codes)

    def test_load_registry_keeps_retired_specs_out_of_active_specs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs_dir = root / ".lattice/specs/examples"
            specs_dir.mkdir(parents=True)
            for spec_id, status in [
                ("ACTIVE-001", "active"),
                ("RETIRED-001", "retired"),
            ]:
                (specs_dir / f"{spec_id}.json").write_text(
                    json.dumps(
                        {
                            "id": spec_id,
                            "kind": "domain_object",
                            "name": spec_id,
                            "owner": "tests",
                            "status": status,
                            "description": spec_id,
                        }
                    ),
                    encoding="utf-8",
                )

            registry = load_registry(load_config(root))

            self.assertIn("RETIRED-001", registry.by_id)
            self.assertEqual(
                ["ACTIVE-001"],
                [spec.id for spec in registry.active_specs],
            )

    def test_spec_registry_compat_reports_pathless_units(self) -> None:
        project_memory = ProjectMemory.build(
            (
                ProjectMemoryUnit(
                    id="UNIT-001",
                    kind="domain_object",
                    source_location=SourceLocation(label="db:unit/1"),
                    data={
                        "id": "UNIT-001",
                        "kind": "domain_object",
                        "name": "Unit",
                        "owner": "tests",
                        "status": "active",
                        "description": "Unit.",
                    },
                ),
            ),
            ProjectMemoryTypes({}),
            (),
            {},
        )

        registry = spec_registry_from_project_memory(project_memory)

        self.assertEqual([], registry.specs)
        self.assertTrue(
            any(issue.code == "LATTICE-COMPAT-001" for issue in registry.issues)
        )


if __name__ == "__main__":
    unittest.main()
