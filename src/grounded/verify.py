from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .command_utils import executable_is_resolvable, first_executable
from .models import Issue, GroundedConfig, Spec
from .registry import SpecRegistry
from .trust_policy import is_claim_bearing_kind


VERIFY_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class VerificationResult:
    verification_id: str
    target_id: str
    command: str
    exit_code: int | None
    passed: bool
    duration_seconds: float | None = None
    issue_code: str | None = None


def verify(
    config: GroundedConfig,
    registry: SpecRegistry,
    *,
    timeout_seconds: float = VERIFY_TIMEOUT_SECONDS,
) -> list[Issue]:
    if registry.issues:
        return list(registry.issues)

    issues: list[Issue] = []
    results: list[VerificationResult] = []
    for spec in registry.active_specs:
        type_def = registry.type_definition_for(spec)
        if type_def is None:
            continue
        for field in type_def.verification_fields:
            result, issue = _run_verification_field(
                config,
                spec,
                field,
                timeout_seconds=timeout_seconds,
            )
            results.append(result)
            if issue is not None:
                issues.append(issue)

    results_by_id = {result.verification_id: result for result in results}
    active_by_id = {spec.id: spec for spec in registry.active_specs}
    for spec in registry.active_specs:
        if spec.data.get("trust_status") != "verified" or not is_claim_bearing_spec(
            spec
        ):
            continue
        verification_refs = spec.data.get("verification_refs")
        if not isinstance(verification_refs, list):
            continue
        for ref in verification_refs:
            if not isinstance(ref, str):
                continue
            verification = active_by_id.get(ref)
            if verification is None or verification.kind != "verification":
                continue
            if verification.data.get("target") != spec.id:
                issues.append(
                    Issue(
                        "GROUNDED-VERIFY-005",
                        (
                            f"{spec.id} is verified by {ref}, but {ref}.target "
                            f"is {verification.data.get('target')!r}"
                        ),
                        spec.path,
                    )
                )
                continue
            result = results_by_id.get(ref)
            if result is None or not result.passed:
                issue_code = (
                    result.issue_code if result is not None else "missing result"
                )
                issues.append(
                    Issue(
                        "GROUNDED-VERIFY-006",
                        (
                            f"{spec.id} is trust_status verified but verification "
                            f"{ref} did not pass: {issue_code}"
                        ),
                        spec.path,
                    )
                )
    return issues


def is_claim_bearing_spec(spec: Spec) -> bool:
    return is_claim_bearing_kind(spec.kind)


def _run_verification_field(
    config: GroundedConfig,
    spec: Spec,
    field: str,
    *,
    timeout_seconds: float,
) -> tuple[VerificationResult, Issue | None]:
    value = spec.data.get(field)
    target_id = spec.data.get("target")
    if not isinstance(target_id, str) or not target_id:
        target_id = spec.id
    if not isinstance(value, str) or not value.strip():
        result = VerificationResult(
            verification_id=spec.id,
            target_id=target_id,
            command="",
            exit_code=None,
            passed=False,
            issue_code="GROUNDED-VERIFY-002",
        )
        return (
            result,
            Issue(
                "GROUNDED-VERIFY-002",
                f"{spec.id}.{field} must contain a non-empty command",
                spec.path,
            ),
        )

    executable = first_executable(value)
    if executable is None or not executable_is_resolvable(executable, cwd=config.root):
        result = VerificationResult(
            verification_id=spec.id,
            target_id=target_id,
            command=value,
            exit_code=None,
            passed=False,
            issue_code="GROUNDED-VERIFY-003",
        )
        return (
            result,
            Issue(
                "GROUNDED-VERIFY-003",
                (
                    f"{spec.id}.{field} command executable cannot be resolved: "
                    f"{executable or value!r}"
                ),
                spec.path,
            ),
        )

    started = time.monotonic()
    try:
        completed = subprocess.run(
            value,
            cwd=config.root,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        result = VerificationResult(
            verification_id=spec.id,
            target_id=target_id,
            command=value,
            exit_code=None,
            passed=False,
            duration_seconds=duration,
            issue_code="GROUNDED-VERIFY-004",
        )
        return (
            result,
            Issue(
                "GROUNDED-VERIFY-004",
                (f"{spec.id}.{field} timed out after {exc.timeout:g}s: {value!r}"),
                spec.path,
            ),
        )

    duration = time.monotonic() - started
    passed = completed.returncode == 0
    result = VerificationResult(
        verification_id=spec.id,
        target_id=target_id,
        command=value,
        exit_code=completed.returncode,
        passed=passed,
        duration_seconds=duration,
        issue_code=None if passed else "GROUNDED-VERIFY-001",
    )
    if passed:
        return result, None
    detail = (
        completed.stderr.strip()
        or completed.stdout.strip()
        or f"exit code {completed.returncode}"
    )
    return (
        result,
        Issue(
            "GROUNDED-VERIFY-001",
            f"{spec.id}.{field} failed: {value!r}: {detail}",
            spec.path,
        ),
    )
