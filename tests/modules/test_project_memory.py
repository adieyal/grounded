from __future__ import annotations

import unittest

from grounded.modules.project_memory import (
    ProjectMemoryFacade,
    ProjectMemoryIssue,
    ProjectMemoryType,
    ProjectMemoryTypes,
    RawProjectMemoryUnit,
    SourceLocation,
)
from grounded.modules.project_memory.application.ports import (
    TypeSourceResult,
    UnitSourceResult,
)


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


class FakeValidator:
    def __init__(self, *issues: ProjectMemoryIssue) -> None:
        self._issues = list(issues)

    def validate(
        self,
        unit: RawProjectMemoryUnit,
        types: ProjectMemoryTypes,
    ) -> list[ProjectMemoryIssue]:
        return list(self._issues)


def raw_unit(unit_id: str, **data: object) -> RawProjectMemoryUnit:
    payload = {
        "id": unit_id,
        "kind": data.pop("kind", "concept"),
        "name": unit_id,
        "owner": "tests",
        "status": data.pop("status", "active"),
        "description": unit_id,
        **data,
    }
    return RawProjectMemoryUnit(payload, SourceLocation(label=f"memory:{unit_id}"))


def project_memory_types() -> ProjectMemoryTypes:
    return ProjectMemoryTypes(
        {
            "concept": ProjectMemoryType(
                type="concept",
                extends=None,
                schema=None,
                schema_path=None,
                renderer="unit.html.j2",
                search_fields=("id", "name"),
                verification_fields=(),
                reference_fields=("references",),
                single_reference_fields=(),
                nested_reference_fields=(),
                reference_tag_constraints=(),
                required=("id", "kind", "name"),
                list_fields=("references",),
            )
        }
    )


class ProjectMemoryTests(unittest.TestCase):
    def load(
        self,
        units: list[RawProjectMemoryUnit],
        validator: FakeValidator | None = None,
    ):
        facade = ProjectMemoryFacade(
            InMemoryUnitSource(*units),
            InMemoryTypeSource(project_memory_types()),
            validator or FakeValidator(),
        )
        return facade.load()

    def test_duplicate_ids_are_detected_without_filesystem_access(self) -> None:
        memory = self.load([raw_unit("UNIT-001"), raw_unit("UNIT-001")])

        self.assertEqual(["GROUNDED-ID-001"], [issue.code for issue in memory.issues])
        self.assertEqual(["UNIT-001"], [unit.id for unit in memory.units])

    def test_active_units_exclude_retired_but_all_units_remain_loaded(self) -> None:
        memory = self.load(
            [
                raw_unit("ACTIVE-001"),
                raw_unit("DRAFT-001", status="draft"),
                raw_unit("RETIRED-001", status="retired"),
            ]
        )

        self.assertEqual(
            ["ACTIVE-001", "DRAFT-001", "RETIRED-001"],
            [unit.id for unit in memory.units],
        )
        self.assertEqual(
            ["ACTIVE-001", "DRAFT-001"],
            [unit.id for unit in memory.active_units],
        )
        self.assertEqual(["RETIRED-001"], [unit.id for unit in memory.retired_units])

    def test_unknown_references_produce_graph_issues(self) -> None:
        memory = self.load([raw_unit("UNIT-001", references=["MISSING-001"])])

        self.assertTrue(
            any(
                issue.code == "GROUNDED-REF-001" and "MISSING-001" in issue.message
                for issue in memory.issues
            )
        )

    def test_backlinks_are_derived_from_valid_references(self) -> None:
        memory = self.load(
            [
                raw_unit("SOURCE-001", references=["TARGET-001"]),
                raw_unit("TARGET-001"),
            ]
        )

        self.assertEqual(("SOURCE-001",), memory.backlinks_by_id["TARGET-001"])

    def test_backlinks_include_empty_entries_for_units_without_backlinks(self) -> None:
        memory = self.load([raw_unit("UNIT-001")])

        self.assertEqual((), memory.backlinks_by_id["UNIT-001"])

    def test_lookup_matches_registry_index_behavior(self) -> None:
        memory = self.load([raw_unit("UNIT-001")])

        self.assertEqual("UNIT-001", memory.get("UNIT-001").id)
        self.assertIsNone(memory.get("MISSING-001"))
        self.assertIn("UNIT-001", memory.by_id)

    def test_shape_validation_issues_are_preserved(self) -> None:
        validator_issue = ProjectMemoryIssue(
            "TEST_SHAPE_ISSUE",
            "fake validator issue",
            SourceLocation(label="validator"),
        )
        memory = self.load([raw_unit("UNIT-001")], FakeValidator(validator_issue))

        self.assertIn(validator_issue, memory.issues)


if __name__ == "__main__":
    unittest.main()
