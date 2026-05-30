from __future__ import annotations

from ..domain.issues import ProjectMemoryIssue
from ..domain.model import ProjectMemoryTypes, RawProjectMemoryUnit, TagRequirement
from ..domain.tags import normalize_tag


def validate_project_memory_shape(
    unit: RawProjectMemoryUnit,
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    data = dict(unit.data)
    kind = _spec_type(data)
    type_def = types.get(kind) if kind is not None else None
    if type_def is None:
        message = (
            f"unknown spec type {kind}; add it to the type registry or correct the spec"
        )
        return [
            ProjectMemoryIssue(
                "GROUNDED-KIND-001",
                message,
                unit.source_location,
            )
        ]

    issues: list[ProjectMemoryIssue] = []
    for field in type_def.required:
        if not _string_field(data, field):
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-SCHEMA-003",
                    f"missing required string field: {field}",
                    unit.source_location,
                )
            )

    for list_field in type_def.list_fields:
        value = data.get(list_field, [])
        if value is not None and not isinstance(value, list):
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-SCHEMA-004",
                    f"{list_field} must be a list when present",
                    unit.source_location,
                )
            )

    issues.extend(_validate_tags(data, (), unit, types))
    return issues


def _spec_type(data: dict[str, object]) -> str | None:
    return _string_field(data, "type") or _string_field(data, "kind")


def _string_field(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _validate_tags(
    value: object,
    path_parts: tuple[str, ...],
    unit: RawProjectMemoryUnit,
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    issues: list[ProjectMemoryIssue] = []
    if isinstance(value, dict):
        for key, item in value.items():
            current_path = (*path_parts, key)
            if key == "tags":
                issues.extend(_validate_tag_list(item, current_path, unit, types))
            else:
                issues.extend(_validate_tags(item, current_path, unit, types))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            issues.extend(_validate_tags(item, (*path_parts, str(index)), unit, types))
    return issues


def _validate_tag_list(
    value: object,
    path_parts: tuple[str, ...],
    unit: RawProjectMemoryUnit,
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [
            ProjectMemoryIssue(
                "GROUNDED-TAG-003",
                f"{'.'.join(path_parts)} must be a list when present",
                unit.source_location,
            )
        ]

    issues: list[ProjectMemoryIssue] = []
    for item in value:
        tag = normalize_tag(item)
        if tag is None:
            message = (
                f"{'.'.join(path_parts)} entries must be strings or typed tag objects"
            )
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TAG-003",
                    message,
                    unit.source_location,
                )
            )
            continue
        if tag.type is not None:
            issues.extend(
                _validate_tag_requirement(
                    TagRequirement(tag.type, tag.value),
                    unit,
                    types,
                )
            )
    return issues


def _validate_tag_requirement(
    requirement: TagRequirement,
    unit: RawProjectMemoryUnit,
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    if not types.tag_type_definitions:
        return []
    tag_def = types.tag_type_definitions.get(requirement.type)
    if tag_def is None:
        return [
            ProjectMemoryIssue(
                "GROUNDED-TAG-001",
                f"unknown tag type {requirement.type}",
                unit.source_location,
            )
        ]
    if tag_def.values and requirement.value not in tag_def.values:
        return [
            ProjectMemoryIssue(
                "GROUNDED-TAG-002",
                f"unknown value {requirement.value} for tag type {requirement.type}",
                unit.source_location,
            )
        ]
    return []
