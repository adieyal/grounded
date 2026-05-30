from __future__ import annotations

from pathlib import Path

from .command_utils import executable_is_resolvable, first_executable
from .modules.project_memory.domain.issues import ProjectMemoryIssue
from .modules.project_memory.domain.model import ProjectMemoryTypes, ProjectMemoryUnit
from .trust_policy import AUTHORED_KNOWLEDGE_CATEGORY, TRUST_STATUSES
from .trust_policy import GENERATED_ARTIFACT_CATEGORY, TRUTH_OWNING_TRUST_STATUSES
from .trust_policy import is_claim_bearing_kind


def is_claim_bearing(unit: ProjectMemoryUnit) -> bool:
    return is_claim_bearing_kind(unit.kind)


def validate_trust_credibility(
    units: tuple[ProjectMemoryUnit, ...],
    types: ProjectMemoryTypes,
    *,
    cwd: Path | None = None,
) -> list[ProjectMemoryIssue]:
    issues: list[ProjectMemoryIssue] = []
    by_id = {unit.id: unit for unit in units}

    for unit in units:
        trust_status = unit.data.get("trust_status")
        if trust_status is not None and trust_status not in TRUST_STATUSES:
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TRUST-001",
                    (
                        f"{unit.id}.trust_status must be one of "
                        f"{', '.join(TRUST_STATUSES)}"
                    ),
                    unit.source_location,
                )
            )
        if unit.status == "active":
            issues.extend(_validate_truth_ownership(unit, types))
        if unit.status == "active" and is_claim_bearing(unit):
            issues.extend(_validate_verified_claim(unit, by_id))
            issues.extend(_validate_checkable_claim(unit, by_id))
            issues.extend(_validate_observed_claim(unit, by_id, types))
        if unit.status == "active":
            issues.extend(_validate_verification_commands(unit, types, cwd=cwd))
    return issues


def _validate_truth_ownership(
    unit: ProjectMemoryUnit, types: ProjectMemoryTypes
) -> list[ProjectMemoryIssue]:
    if unit.data.get("trust_status") not in TRUTH_OWNING_TRUST_STATUSES:
        return []
    if _semantic_category(unit, types) != GENERATED_ARTIFACT_CATEGORY:
        return []
    return [
        ProjectMemoryIssue(
            "GROUNDED-TRUST-005",
            (
                f"{unit.id} is a generated artifact and cannot own truth with "
                f"trust_status {unit.data.get('trust_status')!r}"
            ),
            unit.source_location,
        )
    ]


def _validate_verified_claim(
    unit: ProjectMemoryUnit, by_id: dict[str, ProjectMemoryUnit]
) -> list[ProjectMemoryIssue]:
    if unit.data.get("trust_status") != "verified":
        return []
    verification_refs = unit.data.get("verification_refs")
    if not isinstance(verification_refs, list) or not verification_refs:
        return [
            ProjectMemoryIssue(
                "GROUNDED-TRUST-002",
                (f"{unit.id} is trust_status verified but has no verification_refs"),
                unit.source_location,
            )
        ]

    issues: list[ProjectMemoryIssue] = []
    active_matching_verification = False
    for ref in verification_refs:
        if not isinstance(ref, str):
            continue
        verification = by_id.get(ref)
        if verification is None:
            continue
        if verification.kind != "verification":
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TRUST-003",
                    f"{unit.id}.verification_refs points to non-verification {ref}",
                    unit.source_location,
                )
            )
            continue
        if verification.status != "active":
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TRUST-003",
                    f"{unit.id}.verification_refs points to inactive verification {ref}",
                    unit.source_location,
                )
            )
            continue
        target = verification.data.get("target")
        if target != unit.id:
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TRUST-004",
                    (
                        f"{unit.id}.verification_refs points to {ref}, "
                        f"but {ref}.target is {target!r}"
                    ),
                    unit.source_location,
                )
            )
            continue
        active_matching_verification = True
    if not active_matching_verification:
        issues.append(
            ProjectMemoryIssue(
                "GROUNDED-TRUST-002",
                (
                    f"{unit.id} is trust_status verified but has no active "
                    "verification targeting it"
                ),
                unit.source_location,
            )
        )
    return issues


def _validate_checkable_claim(
    unit: ProjectMemoryUnit, by_id: dict[str, ProjectMemoryUnit]
) -> list[ProjectMemoryIssue]:
    if unit.data.get("trust_status") != "checkable":
        return []
    if _has_active_matching_verification(unit, by_id):
        return []
    if _string_field(unit.data, "trust_basis") is not None:
        return []
    return [
        ProjectMemoryIssue(
            "GROUNDED-TRUST-006",
            (
                f"{unit.id} is trust_status checkable but has no active targeted "
                "verification_ref or trust_basis explaining why it is not wired yet"
            ),
            unit.source_location,
        )
    ]


def _validate_observed_claim(
    unit: ProjectMemoryUnit,
    by_id: dict[str, ProjectMemoryUnit],
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    if unit.data.get("trust_status") != "observed":
        return []
    if _string_field(unit.data, "observed_basis") is not None:
        return []
    if _string_field(unit.data, "evidence") is not None:
        return []
    if _has_authored_knowledge_source_ref(unit, by_id, types):
        return []
    return [
        ProjectMemoryIssue(
            "GROUNDED-TRUST-007",
            (
                f"{unit.id} is trust_status observed but has no observed_basis, "
                "evidence, or source_ref to authored knowledge"
            ),
            unit.source_location,
        )
    ]


def _has_active_matching_verification(
    unit: ProjectMemoryUnit, by_id: dict[str, ProjectMemoryUnit]
) -> bool:
    verification_refs = unit.data.get("verification_refs")
    if not isinstance(verification_refs, list):
        return False
    for ref in verification_refs:
        if not isinstance(ref, str):
            continue
        verification = by_id.get(ref)
        if verification is None:
            continue
        if (
            verification.kind == "verification"
            and verification.status == "active"
            and verification.data.get("target") == unit.id
        ):
            return True
    return False


def _has_authored_knowledge_source_ref(
    unit: ProjectMemoryUnit,
    by_id: dict[str, ProjectMemoryUnit],
    types: ProjectMemoryTypes,
) -> bool:
    refs = unit.data.get("source_refs", [])
    if not isinstance(refs, list):
        return False
    for ref in refs:
        target = by_id.get(ref) if isinstance(ref, str) else None
        if target is None:
            continue
        if _semantic_category(target, types) == AUTHORED_KNOWLEDGE_CATEGORY:
            return True
    return False


def _semantic_category(
    unit: ProjectMemoryUnit, types: ProjectMemoryTypes
) -> str | None:
    type_def = types.get(unit.kind)
    return type_def.semantic_category if type_def is not None else None


def _string_field(data: object, key: str) -> str | None:
    if not isinstance(data, dict):
        return None
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _validate_verification_commands(
    unit: ProjectMemoryUnit, types: ProjectMemoryTypes, *, cwd: Path | None
) -> list[ProjectMemoryIssue]:
    type_def = types.get(unit.kind)
    if type_def is None:
        return []
    issues: list[ProjectMemoryIssue] = []
    for field in type_def.verification_fields:
        value = unit.data.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-VERIFY-002",
                    f"{unit.id}.{field} must contain a non-empty command",
                    unit.source_location,
                )
            )
            continue
        executable = first_executable(value)
        if executable is None or not executable_is_resolvable(executable, cwd=cwd):
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-VERIFY-003",
                    (
                        f"{unit.id}.{field} command executable cannot be resolved: "
                        f"{executable or value!r}"
                    ),
                    unit.source_location,
                )
            )
    return issues
