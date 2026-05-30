from __future__ import annotations

from typing import Any

from .issues import ProjectMemoryIssue
from .model import ProjectMemoryTypes, ProjectMemoryUnit
from .rich_text import rich_text_reference_ids
from .tags import has_typed_tag


def reference_ids_for(
    unit: ProjectMemoryUnit, types: ProjectMemoryTypes
) -> tuple[str, ...]:
    refs: list[str] = []
    type_def = types.get(unit.kind)
    reference_fields = type_def.reference_fields if type_def else ("references",)
    single_reference_fields = type_def.single_reference_fields if type_def else ()
    nested_reference_fields = type_def.nested_reference_fields if type_def else ()

    for field in reference_fields:
        value = unit.data.get(field, [])
        if isinstance(value, list):
            refs.extend(item for item in value if isinstance(item, str))
    for field in single_reference_fields:
        value = unit.data.get(field)
        if isinstance(value, str):
            refs.append(value)
    for path in nested_reference_fields:
        refs.extend(_reference_values_at_path(unit.data, path))
    links = unit.data.get("links", [])
    if isinstance(links, list):
        for link in links:
            target = (
                link
                if isinstance(link, str)
                else link.get("target_id")
                if isinstance(link, dict)
                else None
            )
            if isinstance(target, str):
                refs.append(target)
    refs.extend(rich_text_reference_ids(unit.data))
    return tuple(dict.fromkeys(refs))


def validate_references(
    units: tuple[ProjectMemoryUnit, ...], types: ProjectMemoryTypes
) -> list[ProjectMemoryIssue]:
    issues: list[ProjectMemoryIssue] = []
    by_id = {unit.id: unit for unit in units}

    for unit in units:
        type_def = types.get(unit.kind)
        reference_fields = type_def.reference_fields if type_def else ("references",)
        single_reference_fields = type_def.single_reference_fields if type_def else ()
        nested_reference_fields = type_def.nested_reference_fields if type_def else ()

        for field in reference_fields:
            value = unit.data.get(field, [])
            if not isinstance(value, list):
                continue
            for ref in value:
                if isinstance(ref, str) and ref not in by_id:
                    issues.append(
                        ProjectMemoryIssue(
                            "GROUNDED-REF-001",
                            f"{unit.id}.{field} references unknown spec {ref}",
                            unit.source_location,
                        )
                    )
        for field in single_reference_fields:
            value = unit.data.get(field)
            if isinstance(value, str) and value not in by_id:
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-REF-002",
                        f"{unit.id}.{field} points to unknown spec {value}",
                        unit.source_location,
                    )
                )
        for path in nested_reference_fields:
            for ref in _nested_values(unit.data, path):
                if isinstance(ref, str) and ref not in by_id:
                    issues.append(
                        ProjectMemoryIssue(
                            "GROUNDED-REF-001",
                            f"{unit.id}.{'.'.join(path)} references unknown spec {ref}",
                            unit.source_location,
                        )
                    )
                elif isinstance(ref, list):
                    for item in ref:
                        if isinstance(item, str) and item not in by_id:
                            issues.append(
                                ProjectMemoryIssue(
                                    "GROUNDED-REF-001",
                                    (
                                        f"{unit.id}.{'.'.join(path)} references "
                                        f"unknown spec {item}"
                                    ),
                                    unit.source_location,
                                )
                            )
        links = unit.data.get("links", [])
        if isinstance(links, list):
            for index, link in enumerate(links):
                target = (
                    link
                    if isinstance(link, str)
                    else link.get("target_id")
                    if isinstance(link, dict)
                    else None
                )
                if isinstance(target, str) and target not in by_id:
                    issues.append(
                        ProjectMemoryIssue(
                            "GROUNDED-REF-003",
                            f"{unit.id}.links[{index}] points to unknown spec {target}",
                            unit.source_location,
                        )
                    )
        for target in rich_text_reference_ids(unit.data):
            if target not in by_id:
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-REF-001",
                        (
                            f"{unit.id} inline rich-text link references "
                            f"unknown spec {target}"
                        ),
                        unit.source_location,
                    )
                )
        if type_def is not None:
            issues.extend(_validate_reference_tag_constraints(unit, by_id, types))
    return issues


def _validate_reference_tag_constraints(
    unit: ProjectMemoryUnit,
    by_id: dict[str, ProjectMemoryUnit],
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    type_def = types.get(unit.kind)
    if type_def is None:
        return []

    issues: list[ProjectMemoryIssue] = []
    for constraint in type_def.reference_tag_constraints:
        for ref in _reference_values_at_path(unit.data, constraint.path):
            target = by_id.get(ref)
            if target is None:
                continue
            if has_typed_tag(
                target.data.get("tags", []),
                constraint.requires.type,
                constraint.requires.value,
            ):
                continue
            message = (
                f"{unit.id}.{'.'.join(constraint.path)} references {ref}, "
                f"which is missing required tag {constraint.requires.label}"
            )
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-REF-005",
                    message,
                    unit.source_location,
                )
            )
    return issues


def _reference_values_at_path(
    data: dict[str, Any], path: tuple[str, ...]
) -> tuple[str, ...]:
    refs: list[str] = []
    for value in _nested_values(data, path):
        if isinstance(value, str):
            refs.append(value)
        elif isinstance(value, list):
            refs.extend(item for item in value if isinstance(item, str))
    return tuple(refs)


def _nested_values(data: object, path: tuple[str, ...]) -> list[object]:
    if not path:
        return [data]
    head, *tail = path
    rest = tuple(tail)
    if isinstance(data, dict):
        if head not in data:
            return []
        return _nested_values(data[head], rest)
    if isinstance(data, list):
        values: list[object] = []
        for item in data:
            values.extend(_nested_values(item, path))
        return values
    return []
