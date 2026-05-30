from __future__ import annotations

from pathlib import Path

from .command_utils import executable_is_resolvable, first_executable
from .modules.project_memory.domain.issues import ProjectMemoryIssue
from .modules.project_memory.domain.model import ProjectMemoryTypes, ProjectMemoryUnit
from .trust_policy import TRUST_STATUSES, is_claim_bearing_kind


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
        if unit.status == "active" and is_claim_bearing(unit):
            issues.extend(_validate_verified_claim(unit, by_id))
        if unit.status == "active":
            issues.extend(_validate_verification_commands(unit, types, cwd=cwd))
    return issues


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
