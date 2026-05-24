from __future__ import annotations

import subprocess

from .models import Issue, LatticeConfig
from .registry import SpecRegistry


def verify(config: LatticeConfig, registry: SpecRegistry) -> list[Issue]:
    issues: list[Issue] = []
    for spec in registry.active_specs:
        type_def = registry.type_definition_for(spec)
        if type_def is None:
            continue
        commands = []
        for field in type_def.verification_fields:
            value = spec.data.get(field)
            if isinstance(value, str) and value:
                commands.append((field, value))
        for field, command in commands:
            result = subprocess.run(command, cwd=config.root, shell=True, text=True, capture_output=True, check=False)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
                issues.append(
                    Issue(
                        "LATTICE-VERIFY-001",
                        f"{spec.id}.{field} failed: {command!r}: {detail}",
                        spec.path,
                    )
                )
    return issues
