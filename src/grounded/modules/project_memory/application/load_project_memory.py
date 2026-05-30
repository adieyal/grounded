from __future__ import annotations

from ..domain.issues import ProjectMemoryIssue
from ..domain.model import (
    ProjectMemory,
    ProjectMemoryType,
    ProjectMemoryTypes,
    ProjectMemoryUnit,
    RawProjectMemoryUnit,
)
from ..domain.references import reference_ids_for, validate_references
from .ports import ShapeValidator, TypeSource, UnitSource


def load_project_memory(
    unit_source: UnitSource,
    type_source: TypeSource,
    shape_validator: ShapeValidator,
) -> ProjectMemory:
    type_result = type_source.read_types()
    unit_result = unit_source.read_units()
    issues: list[ProjectMemoryIssue] = [
        *type_result.issues,
        *unit_result.issues,
        *validate_type_definitions(type_result.types),
    ]

    units: list[ProjectMemoryUnit] = []
    seen: dict[str, RawProjectMemoryUnit] = {}
    for raw_unit in unit_result.units:
        unit_id = _string_field(raw_unit.data, "id")
        unit_kind = _spec_type(raw_unit.data)
        if unit_id is None or unit_kind is None:
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-SCHEMA-002",
                    "spec must contain string id and type or kind",
                    raw_unit.source_location,
                )
            )
            continue
        if unit_id in seen:
            first_location = seen[unit_id].source_location.label
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-ID-001",
                    f"duplicate id {unit_id}; first defined at {first_location}",
                    raw_unit.source_location,
                )
            )
            continue

        normalized = dict(raw_unit.data)
        normalized.setdefault("type", unit_kind)
        normalized.setdefault("kind", unit_kind)
        normalized_raw = RawProjectMemoryUnit(normalized, raw_unit.source_location)
        issues.extend(shape_validator.validate(normalized_raw, type_result.types))
        units.append(
            ProjectMemoryUnit(
                id=unit_id,
                kind=unit_kind,
                source_location=raw_unit.source_location,
                data=normalized,
            )
        )
        seen[unit_id] = raw_unit

    unit_tuple = tuple(units)
    issues.extend(validate_references(unit_tuple, type_result.types))
    references_by_id = {
        unit.id: reference_ids_for(unit, type_result.types) for unit in unit_tuple
    }
    return ProjectMemory.build(
        unit_tuple,
        type_result.types,
        tuple(issues),
        references_by_id,
    )


def validate_type_definitions(types: ProjectMemoryTypes) -> list[ProjectMemoryIssue]:
    issues: list[ProjectMemoryIssue] = []
    issues.extend(_validate_type_hierarchy(types))
    for type_name, definition in types.definitions.items():
        if (
            definition.extends is not None
            and definition.extends not in types.definitions
        ):
            message = (
                f"type {type_name} extends unknown parent type {definition.extends}"
            )
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TYPE-004",
                    message,
                    types.source_location,
                )
            )
        issues.extend(_validate_reference_tag_constraint_definitions(definition, types))
    return issues


def _validate_type_hierarchy(types: ProjectMemoryTypes) -> list[ProjectMemoryIssue]:
    issues: list[ProjectMemoryIssue] = []
    reported_cycles: set[frozenset[str]] = set()
    for type_name in types.definitions:
        visited: list[str] = []
        current = types.definitions[type_name]
        while current.extends is not None and current.extends in types.definitions:
            if current.type in set(visited):
                cycle_start = visited.index(current.type)
                cycle_members = (*visited[cycle_start:], current.type)
                cycle_key = frozenset(cycle_members)
                if cycle_key not in reported_cycles:
                    reported_cycles.add(cycle_key)
                    cycle = " -> ".join(cycle_members)
                    issues.append(
                        ProjectMemoryIssue(
                            "GROUNDED-TYPE-011",
                            f"type hierarchy cycle detected: {cycle}",
                            types.source_location,
                        )
                    )
                break
            visited.append(current.type)
            current = types.definitions[current.extends]
    return issues


def _validate_reference_tag_constraint_definitions(
    definition: ProjectMemoryType, types: ProjectMemoryTypes
) -> list[ProjectMemoryIssue]:
    issues: list[ProjectMemoryIssue] = []
    reference_paths = {(field,) for field in definition.reference_fields} | {
        (field,) for field in definition.single_reference_fields
    }
    reference_paths.update(definition.nested_reference_fields)
    for constraint in definition.reference_tag_constraints:
        if constraint.path not in reference_paths:
            message = (
                f"type {definition.type} constrains non-reference field "
                f"{'.'.join(constraint.path)}"
            )
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TYPE-010",
                    message,
                    types.source_location,
                )
            )
        tag_def = types.tag_type_definitions.get(constraint.requires.type)
        if tag_def is None and types.tag_type_definitions:
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TAG-001",
                    f"unknown tag type {constraint.requires.type}",
                    types.source_location,
                )
            )
        elif (
            tag_def is not None
            and tag_def.values
            and constraint.requires.value not in tag_def.values
        ):
            message = (
                f"unknown value {constraint.requires.value} "
                f"for tag type {constraint.requires.type}"
            )
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TAG-002",
                    message,
                    types.source_location,
                )
            )
    return issues


def _spec_type(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    return _string_field(data, "type") or _string_field(data, "kind")


def _string_field(data: object, key: str) -> str | None:
    if not isinstance(data, dict):
        return None
    value = data.get(key)
    return value if isinstance(value, str) and value else None
