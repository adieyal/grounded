from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from grounded.audit import audit_manual_backlinks
from grounded.bootstrap import init_project
from grounded.config import load_config
from grounded.edge_policy import EDGE_TYPES
from grounded.models import Spec
from grounded.modules.project_memory import (
    ProjectMemoryFacade,
    ProjectMemoryType,
    ProjectMemoryTypes,
    RawProjectMemoryUnit,
    SourceLocation,
)
from grounded.modules.project_memory.application.ports import (
    TypeSourceResult,
    UnitSourceResult,
)
from grounded.registry import SpecRegistry, load_registry
from grounded.render import render_all
from grounded.graphviz import graphviz_dot_for
from grounded.render_markdown import render_llm_pack, render_markdown
from grounded.search import build_search_records


class InMemoryUnitSource:
    def __init__(self, *units: RawProjectMemoryUnit) -> None:
        self._units = units

    def read_units(self) -> UnitSourceResult:
        return UnitSourceResult(self._units)


class InMemoryTypeSource:
    def __init__(self, types: ProjectMemoryTypes) -> None:
        self._types = types

    def read_types(self) -> TypeSourceResult:
        return TypeSourceResult(self._types)


class NoopValidator:
    def validate(
        self,
        unit: RawProjectMemoryUnit,
        types: ProjectMemoryTypes,
    ):
        return []


def raw_unit(
    unit_id: str, kind: str = "concept", **data: object
) -> RawProjectMemoryUnit:
    payload = {
        "id": unit_id,
        "kind": kind,
        "name": unit_id,
        "owner": "tests",
        "status": data.pop("status", "active"),
        "description": unit_id,
        **data,
    }
    return RawProjectMemoryUnit(payload, SourceLocation(label=f"memory:{unit_id}"))


def type_def(
    kind: str,
    *,
    semantic_category: str,
    reference_fields: tuple[str, ...] = (),
    single_reference_fields: tuple[str, ...] = (),
) -> ProjectMemoryType:
    return ProjectMemoryType(
        type=kind,
        extends=None,
        schema=None,
        schema_path=None,
        renderer="unit.html.j2",
        search_fields=("id", "name", "description"),
        verification_fields=(),
        reference_fields=reference_fields,
        single_reference_fields=single_reference_fields,
        nested_reference_fields=(),
        reference_tag_constraints=(),
        required=("id", "kind", "name"),
        list_fields=reference_fields,
        semantic_category=semantic_category,
    )


def project_memory_types() -> ProjectMemoryTypes:
    return ProjectMemoryTypes(
        {
            "asset": type_def("asset", semantic_category="generated_artifact"),
            "concept": type_def(
                "concept",
                semantic_category="authored_knowledge",
                reference_fields=(
                    "references",
                    "examples",
                    "tests",
                    "verification_refs",
                ),
            ),
            "document_section": type_def(
                "document_section",
                semantic_category="generated_artifact",
                reference_fields=("source_refs", "asset_refs"),
            ),
            "generated_document": type_def(
                "generated_document",
                semantic_category="generated_artifact",
                reference_fields=("section_refs", "source_refs"),
            ),
            "test_binding": type_def(
                "test_binding",
                semantic_category="registry_infrastructure",
                single_reference_fields=("target",),
            ),
            "verification": type_def(
                "verification",
                semantic_category="registry_infrastructure",
                single_reference_fields=("target",),
            ),
        }
    )


def load_memory(*units: RawProjectMemoryUnit):
    facade = ProjectMemoryFacade(
        InMemoryUnitSource(*units),
        InMemoryTypeSource(project_memory_types()),
        NoopValidator(),
    )
    return facade.load()


class EdgeModelTests(unittest.TestCase):
    def assertIssue(self, issues: object, code: str) -> None:
        self.assertIn(code, [issue.code for issue in issues])

    def assertNoIssue(self, issues: object, code: str) -> None:
        self.assertNotIn(code, [issue.code for issue in issues])

    def test_edge_vocabulary_is_mirrored_in_default_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            schema = json.loads(
                (root / ".grounded/registry/spec-types.json").read_text(
                    encoding="utf-8"
                )
            )

        edge_enum = schema["registry_unit"]["schema"]["properties"]["edges"]["items"][
            "properties"
        ]["type"]["enum"]
        self.assertEqual([*EDGE_TYPES], edge_enum)

    def test_invalid_authored_edge_type_fails_validation(self) -> None:
        memory = load_memory(
            raw_unit(
                "SOURCE-001",
                edges=[{"type": "handwaves_at", "target": "TARGET-001"}],
            ),
            raw_unit("TARGET-001"),
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-003")

    def test_authored_edge_missing_target_fails_validation(self) -> None:
        memory = load_memory(raw_unit("SOURCE-001", edges=[{"type": "mentions"}]))

        self.assertIssue(memory.issues, "GROUNDED-EDGE-002")

    def test_authored_edge_target_must_resolve(self) -> None:
        memory = load_memory(
            raw_unit("SOURCE-001", edges=[{"type": "mentions", "target": "NOPE-001"}])
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-004")

    def test_legacy_fields_normalize_into_typed_edges(self) -> None:
        memory = load_memory(
            raw_unit(
                "SOURCE-001",
                references=["REF-001"],
                examples=["EXAMPLE-001"],
                tests=["TEST-001"],
                verification_refs=["VERIFY-001"],
            ),
            raw_unit("REF-001"),
            raw_unit("EXAMPLE-001"),
            raw_unit("TEST-001", kind="test_binding", target="SOURCE-001"),
            raw_unit(
                "VERIFY-001",
                kind="verification",
                target="SOURCE-001",
            ),
        )

        observed = {
            (edge.source_id, edge.edge_type, edge.target_id, edge.source_field)
            for edge in memory.normalized_edges
        }
        self.assertIn(("SOURCE-001", "mentions", "REF-001", "references"), observed)
        self.assertIn(("SOURCE-001", "mentions", "EXAMPLE-001", "examples"), observed)
        self.assertIn(("SOURCE-001", "tests", "TEST-001", "tests"), observed)
        self.assertIn(
            ("SOURCE-001", "verified_by", "VERIFY-001", "verification_refs"),
            observed,
        )

    def test_verification_target_creates_computed_inverse_verified_by_edge(
        self,
    ) -> None:
        memory = load_memory(
            raw_unit("SOURCE-001"),
            raw_unit("VERIFY-001", kind="verification", target="SOURCE-001"),
        )

        observed = {
            (edge.source_id, edge.edge_type, edge.target_id, edge.source_field)
            for edge in memory.normalized_edges
        }
        self.assertIn(("SOURCE-001", "verified_by", "VERIFY-001", "target"), observed)
        self.assertEqual(("SOURCE-001",), memory.backlinks_by_id["VERIFY-001"])
        self.assertEqual(
            ("VERIFY-001",),
            tuple(edge.target_id for edge in memory.outgoing_edges_by_id["SOURCE-001"]),
        )

    def test_generated_artifact_fields_normalize_into_projection_edges(self) -> None:
        memory = load_memory(
            raw_unit(
                "DOC-001",
                kind="generated_document",
                source_refs=["SOURCE-001"],
                section_refs=["SECTION-001"],
            ),
            raw_unit(
                "SECTION-001",
                kind="document_section",
                source_refs=["SOURCE-001"],
                asset_refs=["ASSET-001"],
            ),
            raw_unit("SOURCE-001"),
            raw_unit("ASSET-001", kind="asset"),
        )

        observed = {
            (edge.source_id, edge.edge_type, edge.target_id, edge.source_field)
            for edge in memory.normalized_edges
        }
        self.assertIn(
            ("DOC-001", "derives_from", "SOURCE-001", "source_refs"), observed
        )
        self.assertIn(("DOC-001", "contains", "SECTION-001", "section_refs"), observed)
        self.assertIn(
            ("SECTION-001", "contains", "ASSET-001", "asset_refs"),
            observed,
        )

    def test_authored_claim_source_refs_normalize_to_mentions_not_projection(
        self,
    ) -> None:
        memory = load_memory(
            raw_unit(
                "CLAIM-001",
                trust_status="observed",
                source_refs=["SOURCE-001"],
            ),
            raw_unit("SOURCE-001"),
        )

        observed = {
            (edge.source_id, edge.edge_type, edge.target_id, edge.source_field)
            for edge in memory.normalized_edges
        }
        self.assertIn(("CLAIM-001", "mentions", "SOURCE-001", "source_refs"), observed)
        self.assertNoIssue(memory.issues, "GROUNDED-EDGE-006")
        self.assertNoIssue(memory.issues, "GROUNDED-TRUST-007")

    def test_generated_artifact_source_refs_still_normalize_to_derives_from(
        self,
    ) -> None:
        memory = load_memory(
            raw_unit(
                "DOC-001",
                kind="generated_document",
                source_refs=["SOURCE-001"],
            ),
            raw_unit("SOURCE-001"),
        )

        observed = {
            (edge.source_id, edge.edge_type, edge.target_id, edge.source_field)
            for edge in memory.normalized_edges
        }
        self.assertIn(
            ("DOC-001", "derives_from", "SOURCE-001", "source_refs"), observed
        )

    def test_verified_by_target_must_be_verification_or_test_binding(self) -> None:
        memory = load_memory(
            raw_unit(
                "SOURCE-001",
                edges=[{"type": "verified_by", "target": "TARGET-001"}],
            ),
            raw_unit("TARGET-001"),
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-005")

    def test_verified_by_verification_target_mismatch_fails(self) -> None:
        memory = load_memory(
            raw_unit(
                "SOURCE-001",
                edges=[{"type": "verified_by", "target": "VERIFY-001"}],
            ),
            raw_unit("OTHER-001"),
            raw_unit("VERIFY-001", kind="verification", target="OTHER-001"),
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-005")

    def test_projection_edges_cannot_use_generated_artifacts_as_truth_owners(
        self,
    ) -> None:
        memory = load_memory(
            raw_unit(
                "DOC-001",
                kind="generated_document",
                edges=[{"type": "derives_from", "target": "SECTION-001"}],
            ),
            raw_unit("SECTION-001", kind="document_section"),
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-006")

    def test_documents_edge_must_start_from_generated_artifact(self) -> None:
        memory = load_memory(
            raw_unit(
                "SOURCE-001",
                edges=[{"type": "documents", "target": "TARGET-001"}],
            ),
            raw_unit("TARGET-001"),
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-006")

    def test_illustrated_by_target_must_be_asset(self) -> None:
        memory = load_memory(
            raw_unit(
                "SOURCE-001",
                edges=[{"type": "illustrated_by", "target": "TARGET-001"}],
            ),
            raw_unit("TARGET-001"),
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-007")

    def test_implements_cannot_target_generated_artifact(self) -> None:
        memory = load_memory(
            raw_unit(
                "SOURCE-001",
                edges=[{"type": "implements", "target": "DOC-001"}],
            ),
            raw_unit("DOC-001", kind="generated_document"),
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-008")

    def test_depends_on_cannot_target_generated_artifact(self) -> None:
        memory = load_memory(
            raw_unit(
                "SOURCE-001",
                edges=[{"type": "depends_on", "target": "DOC-001"}],
            ),
            raw_unit("DOC-001", kind="generated_document"),
        )

        self.assertIssue(memory.issues, "GROUNDED-EDGE-008")

    def test_depends_on_layer_direction_is_validated_when_both_sides_declare_layer(
        self,
    ) -> None:
        passing = load_memory(
            raw_unit(
                "APP-001",
                semantic_layer="application",
                edges=[{"type": "depends_on", "target": "DOMAIN-001"}],
            ),
            raw_unit("DOMAIN-001", semantic_layer="domain"),
        )
        failing = load_memory(
            raw_unit(
                "DOMAIN-001",
                semantic_layer="domain",
                edges=[{"type": "depends_on", "target": "APP-001"}],
            ),
            raw_unit("APP-001", semantic_layer="application"),
        )

        self.assertNoIssue(passing.issues, "GROUNDED-EDGE-010")
        self.assertIssue(failing.issues, "GROUNDED-EDGE-010")

    def test_no_layer_validation_occurs_when_either_side_lacks_layer(self) -> None:
        memory = load_memory(
            raw_unit(
                "DOMAIN-001",
                semantic_layer="domain",
                edges=[{"type": "depends_on", "target": "APP-001"}],
            ),
            raw_unit("APP-001"),
        )

        self.assertNoIssue(memory.issues, "GROUNDED-EDGE-010")

    def test_manual_backlink_fields_emit_audit_warning(self) -> None:
        registry = SpecRegistry(
            specs=[
                Spec(
                    id="ASSET-001",
                    kind="asset",
                    path=Path("ASSET-001.json"),
                    data={
                        "id": "ASSET-001",
                        "kind": "asset",
                        "name": "Asset",
                        "status": "active",
                        "used_by": ["DOC-001"],
                    },
                )
            ],
            issues=[],
            type_defs={},
        )

        issues = audit_manual_backlinks(registry)

        self.assertIssue(issues, "GROUNDED-EDGE-011")

    def test_manual_used_by_does_not_create_computed_backlink(self) -> None:
        memory = load_memory(
            raw_unit("ASSET-001", kind="asset", used_by=["DOC-001"]),
            raw_unit("DOC-001", kind="generated_document"),
        )

        self.assertEqual((), memory.backlinks_by_id["DOC-001"])

    def test_search_records_include_typed_edge_groups(self) -> None:
        registry = SpecRegistry(
            specs=[
                Spec(
                    id="SOURCE-001",
                    kind="concept",
                    path=Path("SOURCE-001.json"),
                    data={
                        "id": "SOURCE-001",
                        "kind": "concept",
                        "name": "Source",
                        "status": "active",
                        "references": ["TARGET-001"],
                    },
                ),
                Spec(
                    id="TARGET-001",
                    kind="concept",
                    path=Path("TARGET-001.json"),
                    data={
                        "id": "TARGET-001",
                        "kind": "concept",
                        "name": "Target",
                        "status": "active",
                    },
                ),
            ],
            issues=[],
            type_defs={},
        )

        records = {record.id: record for record in build_search_records(registry)}

        self.assertEqual(("mentions:TARGET-001",), records["SOURCE-001"].outgoing_edges)
        self.assertEqual(("mentions:SOURCE-001",), records["TARGET-001"].incoming_edges)

    def test_registry_edge_lookup_uses_indexed_normalized_edges(self) -> None:
        registry = SpecRegistry(
            specs=[
                Spec(
                    id="SOURCE-001",
                    kind="concept",
                    path=Path("SOURCE-001.json"),
                    data={
                        "id": "SOURCE-001",
                        "kind": "concept",
                        "name": "Source",
                        "status": "active",
                        "edges": [{"type": "depends_on", "target": "TARGET-001"}],
                    },
                ),
                Spec(
                    id="TARGET-001",
                    kind="concept",
                    path=Path("TARGET-001.json"),
                    data={
                        "id": "TARGET-001",
                        "kind": "concept",
                        "name": "Target",
                        "status": "active",
                    },
                ),
            ],
            issues=[],
            type_defs={},
        )

        self.assertEqual(
            ("TARGET-001",),
            tuple(edge.target_id for edge in registry.outgoing_edges_for("SOURCE-001")),
        )
        self.assertEqual(
            ("SOURCE-001",),
            tuple(edge.source_id for edge in registry.incoming_edges_for("TARGET-001")),
        )

    def test_graphviz_uses_authored_typed_edges(self) -> None:
        registry = SpecRegistry(
            specs=[
                Spec(
                    id="SOURCE-001",
                    kind="concept",
                    path=Path("SOURCE-001.json"),
                    data={
                        "id": "SOURCE-001",
                        "kind": "concept",
                        "name": "Source",
                        "status": "active",
                        "edges": [{"type": "depends_on", "target": "TARGET-001"}],
                    },
                ),
                Spec(
                    id="TARGET-001",
                    kind="concept",
                    path=Path("TARGET-001.json"),
                    data={
                        "id": "TARGET-001",
                        "kind": "concept",
                        "name": "Target",
                        "status": "active",
                    },
                ),
            ],
            issues=[],
            type_defs={},
        )

        debug_dot = graphviz_dot_for(registry, "SOURCE-001", depth=1, profile="debug")
        docs_dot = graphviz_dot_for(registry, "SOURCE-001", depth=1, profile="docs")

        self.assertIn('"SOURCE-001" -> "TARGET-001";', debug_dot)
        self.assertIn('"SOURCE-001" -> "TARGET-001" [label="depends on"];', docs_dot)

    def test_markdown_context_outputs_typed_edges(self) -> None:
        registry = SpecRegistry(
            specs=[
                Spec(
                    id="SOURCE-001",
                    kind="concept",
                    path=Path("SOURCE-001.json"),
                    data={
                        "id": "SOURCE-001",
                        "kind": "concept",
                        "name": "Source",
                        "status": "active",
                        "edges": [{"type": "depends_on", "target": "TARGET-001"}],
                    },
                ),
                Spec(
                    id="TARGET-001",
                    kind="concept",
                    path=Path("TARGET-001.json"),
                    data={
                        "id": "TARGET-001",
                        "kind": "concept",
                        "name": "Target",
                        "status": "active",
                    },
                ),
            ],
            issues=[],
            type_defs={},
        )

        context_pack = render_llm_pack(registry)
        markdown = render_markdown(registry)

        self.assertIn("Edges: depends_on -> TARGET-001", context_pack)
        self.assertIn("Incoming edges: depends_on <- SOURCE-001", context_pack)
        self.assertIn("Edges: `depends_on` -> `TARGET-001`", markdown)
        self.assertIn("Incoming edges: `depends_on` <- `SOURCE-001`", markdown)

    def test_rendered_links_are_grouped_by_typed_edge_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            (specs_dir / "SOURCE-001.json").write_text(
                json.dumps(
                    {
                        "id": "SOURCE-001",
                        "kind": "domain_object",
                        "name": "Source",
                        "owner": "tests",
                        "status": "active",
                        "description": "A source spec.",
                        "references": ["TARGET-001"],
                    }
                ),
                encoding="utf-8",
            )
            (specs_dir / "TARGET-001.json").write_text(
                json.dumps(
                    {
                        "id": "TARGET-001",
                        "kind": "domain_object",
                        "name": "Target",
                        "owner": "tests",
                        "status": "active",
                        "description": "A target spec.",
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(root)
            registry = load_registry(config)

            self.assertEqual([], registry.issues)
            render_all(config, registry)
            html = (root / ".grounded/generated/docs/units/source-001.html").read_text(
                encoding="utf-8"
            )

        self.assertIn("Outgoing Typed Edges", html)
        self.assertIn("Mentions", html)


if __name__ == "__main__":
    unittest.main()
