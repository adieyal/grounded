from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from .issues import ProjectMemoryIssue


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class SourceLocation:
    """Source-neutral location with an optional filesystem path for compatibility."""

    label: str
    path: Path | None = None

    @classmethod
    def from_path(cls, path: Path) -> "SourceLocation":
        return cls(label=str(path), path=path)


@dataclass(frozen=True)
class RawProjectMemoryUnit:
    data: Mapping[str, Any]
    source_location: SourceLocation


@dataclass(frozen=True)
class TagTypeDefinition:
    type: str
    values: tuple[str, ...]
    description: str | None = None


@dataclass(frozen=True)
class TagRequirement:
    type: str
    value: str

    @property
    def label(self) -> str:
        return f"{self.type}:{self.value}"


@dataclass(frozen=True)
class ReferenceTagConstraint:
    path: tuple[str, ...]
    requires: TagRequirement


@dataclass(frozen=True)
class ProjectMemoryType:
    type: str
    extends: str | None
    schema: dict[str, Any] | None
    schema_path: str | None
    renderer: str
    search_fields: tuple[str, ...]
    verification_fields: tuple[str, ...]
    reference_fields: tuple[str, ...]
    single_reference_fields: tuple[str, ...]
    nested_reference_fields: tuple[tuple[str, ...], ...]
    reference_tag_constraints: tuple[ReferenceTagConstraint, ...]
    required: tuple[str, ...]
    list_fields: tuple[str, ...]
    semantic_category: str | None = None

    @property
    def kind(self) -> str:
        return self.type


@dataclass(frozen=True)
class ProjectMemoryTypes:
    definitions: Mapping[str, ProjectMemoryType]
    tag_type_definitions: Mapping[str, TagTypeDefinition] = field(default_factory=dict)
    source_location: SourceLocation | None = None

    def get(self, unit_kind: str) -> ProjectMemoryType | None:
        return self.definitions.get(unit_kind)

    def schema_chain(
        self, type_def: ProjectMemoryType
    ) -> tuple[ProjectMemoryType, ...]:
        """Resolve the Grounded type hierarchy; validators decide how to use schemas."""

        chain: list[ProjectMemoryType] = []
        seen: set[str] = set()
        current: ProjectMemoryType | None = type_def
        while current is not None:
            if current.type in seen:
                break
            seen.add(current.type)
            chain.append(current)
            current = self.definitions.get(current.extends) if current.extends else None
        return tuple(reversed(chain))


@dataclass(frozen=True)
class ProjectMemoryUnit:
    id: str
    kind: str
    source_location: SourceLocation
    data: JsonObject

    @property
    def status(self) -> str:
        value = self.data.get("status")
        return value if isinstance(value, str) else "active"


@dataclass(frozen=True)
class ProjectMemory:
    units: tuple[ProjectMemoryUnit, ...]
    types: ProjectMemoryTypes
    issues: tuple[ProjectMemoryIssue, ...]
    backlinks_by_id: Mapping[str, tuple[str, ...]]

    @property
    def by_id(self) -> dict[str, ProjectMemoryUnit]:
        return {unit.id: unit for unit in self.units}

    @property
    def active_units(self) -> tuple[ProjectMemoryUnit, ...]:
        return tuple(unit for unit in self.units if unit.status != "retired")

    @property
    def retired_units(self) -> tuple[ProjectMemoryUnit, ...]:
        return tuple(unit for unit in self.units if unit.status == "retired")

    def get(self, unit_id: str) -> ProjectMemoryUnit | None:
        return self.by_id.get(unit_id)

    @classmethod
    def build(
        cls,
        units: tuple[ProjectMemoryUnit, ...],
        types: ProjectMemoryTypes,
        issues: tuple[ProjectMemoryIssue, ...],
        references_by_id: Mapping[str, tuple[str, ...]],
    ) -> "ProjectMemory":
        backlinks: dict[str, list[str]] = defaultdict(list)
        unit_ids = {unit.id for unit in units}
        for source_id, targets in references_by_id.items():
            for target_id in targets:
                if target_id in unit_ids:
                    backlinks[target_id].append(source_id)
        return cls(
            units=units,
            types=types,
            issues=issues,
            backlinks_by_id={
                unit.id: tuple(sorted(backlinks.get(unit.id, ()))) for unit in units
            },
        )
