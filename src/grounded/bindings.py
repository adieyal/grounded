from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .models import Spec
    from .modules.project_memory.domain.model import (
        ProjectMemoryType,
        ProjectMemoryUnit,
    )


BindingRole = Literal[
    "implementation",
    "test",
    "verification",
    "schema",
    "route",
    "documentation",
    "generated_artifact",
]
BindingTargetKind = str
BindingOmissionReason = Literal[
    "include_bindings_not_requested",
    "missing_path",
    "unsupported_target_kind",
    "invalid_binding",
    "lower_priority",
    "limit_exhausted",
    "budget_exhausted",
]

ALLOWED_BINDING_ROLES = {
    "implementation",
    "test",
    "verification",
    "schema",
    "route",
    "documentation",
    "generated_artifact",
}


@dataclass(frozen=True)
class BindingTarget:
    kind: BindingTargetKind
    path: str | None = None
    media_type: str | None = None


@dataclass(frozen=True)
class BindingContextPolicy:
    include_by_default: bool = True
    include_when: str | None = None
    priority: int = 50


@dataclass(frozen=True)
class BindingValidationPolicy:
    path_exists: bool = False
    missing: str = "error"


@dataclass(frozen=True)
class BindingFieldMapping:
    field: str
    role: str
    target_kind: str
    media_type: str | None
    cardinality: str
    validation: BindingValidationPolicy
    context: BindingContextPolicy


@dataclass(frozen=True)
class BindingIssue:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class Binding:
    id: str
    source_spec_id: str
    source_field: str | None
    role: str
    target: BindingTarget
    context: BindingContextPolicy
    validation: BindingValidationPolicy
    validation_issues: tuple[BindingIssue, ...] = ()

    @property
    def validation_status(self) -> str:
        if any(issue.severity == "error" for issue in self.validation_issues):
            return "error"
        if self.validation_issues:
            return "warning"
        return "ok"


@dataclass(frozen=True)
class BindingNormalization:
    bindings: tuple[Binding, ...]
    issues: tuple[BindingIssue, ...]


def validate_binding_field_mapping_entries(
    type_name: str, entries: object
) -> tuple[BindingIssue, ...]:
    if entries is None:
        return ()
    if not isinstance(entries, list):
        return (
            BindingIssue(
                "GROUNDED-BINDING-005",
                f"type {type_name} binding_field_mappings must be a list",
            ),
        )
    issues: list[BindingIssue] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-005",
                    (
                        f"type {type_name} binding_field_mappings[{index}] "
                        "must be an object"
                    ),
                )
            )
    return tuple(issues)


def is_bindable_type(type_def: ProjectMemoryType | None) -> bool:
    return type_def is not None and "bindable" in type_def.capabilities


def validate_binding_type_definition(
    type_def: ProjectMemoryType,
) -> tuple[BindingIssue, ...]:
    issues: list[BindingIssue] = []
    unknown_capabilities = [
        capability
        for capability in type_def.capabilities
        if capability not in {"bindable"}
    ]
    for capability in unknown_capabilities:
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-010",
                f"type {type_def.type} declares unknown capability {capability}",
            )
        )
    if type_def.binding_field_mappings and not is_bindable_type(type_def):
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-011",
                f"type {type_def.type} declares binding_field_mappings but is not bindable",
            )
        )
    for raw_mapping in type_def.binding_field_mappings:
        _parse_mapping(raw_mapping, issues=issues, type_name=type_def.type)
    return tuple(issues)


def bindings_for_spec(
    spec: Spec, type_def: ProjectMemoryType | None, *, project_root: Path | None = None
) -> BindingNormalization:
    return _bindings_for_data(spec.id, spec.data, type_def, project_root=project_root)


def bindings_for_unit(
    unit: ProjectMemoryUnit,
    type_def: ProjectMemoryType | None,
    *,
    project_root: Path | None = None,
) -> BindingNormalization:
    return _bindings_for_data(unit.id, unit.data, type_def, project_root=project_root)


def _bindings_for_data(
    source_spec_id: str,
    data: dict[str, Any],
    type_def: ProjectMemoryType | None,
    *,
    project_root: Path | None,
) -> BindingNormalization:
    bindable = is_bindable_type(type_def)
    issues: list[BindingIssue] = []
    bindings: list[Binding] = []

    if "bindings" in data and not bindable:
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-001",
                f"{source_spec_id} declares bindings but type is not bindable",
            )
        )
        return BindingNormalization((), tuple(issues))

    if not bindable or type_def is None:
        return BindingNormalization((), ())

    explicit = data.get("bindings")
    if explicit is not None:
        bindings.extend(
            _explicit_bindings(
                source_spec_id,
                explicit,
                project_root=project_root,
                issues=issues,
            )
        )

    for raw_mapping in type_def.binding_field_mappings:
        mapping = _parse_mapping(raw_mapping, issues=issues, type_name=type_def.type)
        if mapping is None:
            continue
        if mapping.field not in data:
            continue
        bindings.extend(
            _mapped_bindings(
                source_spec_id,
                data[mapping.field],
                mapping,
                project_root=project_root,
                issues=issues,
            )
        )

    duplicate_ids = _duplicates(binding.id for binding in bindings)
    for binding_id in duplicate_ids:
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-002",
                f"{source_spec_id} declares duplicate binding id {binding_id}",
            )
        )

    return BindingNormalization(tuple(bindings), tuple(issues))


def _explicit_bindings(
    source_spec_id: str,
    value: object,
    *,
    project_root: Path | None,
    issues: list[BindingIssue],
) -> list[Binding]:
    if not isinstance(value, list):
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-003",
                f"{source_spec_id}.bindings must be a list when present",
            )
        )
        return []

    bindings: list[Binding] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-003",
                    f"{source_spec_id}.bindings[{index}] must be an object",
                )
            )
            continue
        role = item.get("role")
        target = item.get("target")
        binding_id = item.get("id") or f"{source_spec_id}:bindings:{index}"
        if not isinstance(binding_id, str) or not binding_id:
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-003",
                    f"{source_spec_id}.bindings[{index}].id must be a non-empty string",
                )
            )
            continue
        if not isinstance(role, str):
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-003",
                    f"{source_spec_id}.bindings[{index}].role must be a string",
                )
            )
            continue
        if not isinstance(target, dict):
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-003",
                    f"{source_spec_id}.bindings[{index}].target must be an object",
                )
            )
            continue

        context = _context_policy(item.get("include"))
        validation = _validation_policy(item.get("validation"))
        binding = _binding_from_target(
            binding_id,
            source_spec_id,
            None,
            role,
            target,
            context,
            validation,
            project_root=project_root,
        )
        bindings.append(binding)
    return bindings


def _mapped_bindings(
    source_spec_id: str,
    value: object,
    mapping: BindingFieldMapping,
    *,
    project_root: Path | None,
    issues: list[BindingIssue],
) -> list[Binding]:
    if mapping.cardinality == "one":
        if isinstance(value, list):
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-004",
                    f"{source_spec_id}.{mapping.field} must be a scalar binding path",
                )
            )
            return []
        if not isinstance(value, str) or not value:
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-004",
                    f"{source_spec_id}.{mapping.field} must be a non-empty string",
                )
            )
            return []
        return [
            _file_binding(
                f"{source_spec_id}:{mapping.field}",
                source_spec_id,
                mapping.field,
                mapping.role,
                value,
                mapping.media_type,
                mapping.context,
                mapping.validation,
                project_root=project_root,
            )
        ]

    if mapping.cardinality == "many":
        if not isinstance(value, list):
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-004",
                    f"{source_spec_id}.{mapping.field} must be a list of binding paths",
                )
            )
            return []
        bindings: list[Binding] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                issues.append(
                    BindingIssue(
                        "GROUNDED-BINDING-004",
                        f"{source_spec_id}.{mapping.field}[{index}] must be a non-empty string",
                    )
                )
                continue
            bindings.append(
                _file_binding(
                    f"{source_spec_id}:{mapping.field}:{index}",
                    source_spec_id,
                    mapping.field,
                    mapping.role,
                    item,
                    mapping.media_type,
                    mapping.context,
                    mapping.validation,
                    project_root=project_root,
                )
            )
        return bindings

    issues.append(
        BindingIssue(
            "GROUNDED-BINDING-004",
            f"{source_spec_id}.{mapping.field} mapping has invalid cardinality {mapping.cardinality}",
        )
    )
    return []


def _parse_mapping(
    value: dict[str, Any], *, issues: list[BindingIssue], type_name: str
) -> BindingFieldMapping | None:
    field = value.get("field")
    role = value.get("role")
    target = value.get("target", {})
    cardinality = value.get("cardinality", "one")
    if not isinstance(field, str) or not field:
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-005",
                f"type {type_name} binding_field_mappings entries require field",
            )
        )
        return None
    if not isinstance(role, str) or role not in ALLOWED_BINDING_ROLES:
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-005",
                f"type {type_name} binding mapping {field} has invalid role",
            )
        )
        return None
    if cardinality not in {"one", "many"}:
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-005",
                f"type {type_name} binding mapping {field} has invalid cardinality",
            )
        )
        return None
    if not isinstance(target, dict):
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-005",
                f"type {type_name} binding mapping {field} target must be an object",
            )
        )
        return None
    target_kind = target.get("kind", "file")
    media_type = target.get("media_type")
    if not isinstance(target_kind, str):
        target_kind = "file"
    if target_kind != "file":
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-005",
                f"type {type_name} binding mapping {field} has unsupported target kind {target_kind}",
            )
        )
        return None
    if media_type is not None and not isinstance(media_type, str):
        media_type = None
    return BindingFieldMapping(
        field=field,
        role=role,
        target_kind=target_kind,
        media_type=media_type,
        cardinality=cardinality,
        validation=_validation_policy(value.get("validation")),
        context=_context_policy(value.get("context")),
    )


def _binding_from_target(
    binding_id: str,
    source_spec_id: str,
    source_field: str | None,
    role: str,
    target: dict[str, Any],
    context: BindingContextPolicy,
    validation: BindingValidationPolicy,
    *,
    project_root: Path | None,
) -> Binding:
    kind = target.get("kind")
    if kind != "file":
        target_kind = kind if isinstance(kind, str) and kind else "unknown"
        return Binding(
            id=binding_id,
            source_spec_id=source_spec_id,
            source_field=source_field,
            role=role,
            target=BindingTarget(kind=target_kind),
            context=context,
            validation=validation,
            validation_issues=(
                BindingIssue(
                    "GROUNDED-BINDING-006",
                    f"{binding_id} uses unsupported target kind {kind!r}",
                ),
            ),
        )
    path = target.get("path")
    media_type = target.get("media_type")
    return _file_binding(
        binding_id,
        source_spec_id,
        source_field,
        role,
        path,
        media_type if isinstance(media_type, str) else None,
        context,
        validation,
        project_root=project_root,
    )


def _file_binding(
    binding_id: str,
    source_spec_id: str,
    source_field: str | None,
    role: str,
    path_value: object,
    media_type: str | None,
    context: BindingContextPolicy,
    validation: BindingValidationPolicy,
    *,
    project_root: Path | None,
) -> Binding:
    validation_issues: list[BindingIssue] = []
    path = _normalize_binding_path(path_value) if isinstance(path_value, str) else ""
    if role not in ALLOWED_BINDING_ROLES:
        validation_issues.append(
            BindingIssue(
                "GROUNDED-BINDING-007", f"{binding_id} has invalid role {role}"
            )
        )
    validation_issues.extend(
        _validate_file_path(binding_id, path, validation, project_root=project_root)
    )
    return Binding(
        id=binding_id,
        source_spec_id=source_spec_id,
        source_field=source_field,
        role=role,
        target=BindingTarget(kind="file", path=path, media_type=media_type),
        context=context,
        validation=validation,
        validation_issues=tuple(validation_issues),
    )


def _validate_file_path(
    binding_id: str,
    path_value: str,
    validation: BindingValidationPolicy,
    *,
    project_root: Path | None,
) -> list[BindingIssue]:
    issues: list[BindingIssue] = []
    if not path_value:
        return [
            BindingIssue(
                "GROUNDED-BINDING-008",
                f"{binding_id} file binding path must be a non-empty string",
            )
        ]
    if _is_windows_absolute_path(path_value):
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-008",
                f"{binding_id} file binding path must be repo-relative",
            )
        )
    if _is_home_relative_path(path_value):
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-008",
                f"{binding_id} file binding path must be repo-relative",
            )
        )
    path = Path(path_value)
    if path.is_absolute():
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-008",
                f"{binding_id} file binding path must be repo-relative",
            )
        )
    if ".." in path.parts:
        issues.append(
            BindingIssue(
                "GROUNDED-BINDING-008",
                f"{binding_id} file binding path must not contain '..'",
            )
        )
    if project_root is not None and not path.is_absolute() and ".." not in path.parts:
        root = project_root.resolve()
        candidate = root / path
        try:
            candidate.resolve(strict=False).relative_to(root)
        except ValueError:
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-008",
                    f"{binding_id} file binding path escapes the project root",
                )
            )
        if candidate.exists():
            try:
                candidate.resolve().relative_to(root)
            except ValueError:
                issues.append(
                    BindingIssue(
                        "GROUNDED-BINDING-008",
                        f"{binding_id} resolved file binding path escapes the project root",
                    )
                )
        elif validation.path_exists:
            issues.append(
                BindingIssue(
                    "GROUNDED-BINDING-009",
                    f"{binding_id} file binding path does not exist: {path_value}",
                    validation.missing,
                )
            )
    return issues


def _normalize_binding_path(path_value: str) -> str:
    return path_value.replace("\\", "/")


def _is_windows_absolute_path(path_value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:", path_value)) or path_value.startswith("//")


def _is_home_relative_path(path_value: str) -> bool:
    return path_value == "~" or path_value.startswith("~/")


def _context_policy(value: object) -> BindingContextPolicy:
    if not isinstance(value, dict):
        return BindingContextPolicy()
    include_by_default = value.get("include_by_default", value.get("default", True))
    include_when = value.get("include_when", value.get("when"))
    priority = value.get("priority", 50)
    return BindingContextPolicy(
        include_by_default=include_by_default
        if isinstance(include_by_default, bool)
        else True,
        include_when=include_when if isinstance(include_when, str) else None,
        priority=priority if isinstance(priority, int) else 50,
    )


def _validation_policy(value: object) -> BindingValidationPolicy:
    if not isinstance(value, dict):
        return BindingValidationPolicy()
    path_exists = value.get("path_exists", False)
    missing = value.get("missing", value.get("severity", "error"))
    return BindingValidationPolicy(
        path_exists=path_exists if isinstance(path_exists, bool) else False,
        missing=missing if missing in {"error", "warning", "info"} else "error",
    )


def _duplicates(values: object) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return tuple(duplicates)
