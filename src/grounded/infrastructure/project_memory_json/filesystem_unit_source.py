from __future__ import annotations

import json

from ...models import GroundedConfig
from ...modules.project_memory.application.ports import UnitSourceResult
from ...modules.project_memory.domain.issues import ProjectMemoryIssue
from ...modules.project_memory.domain.model import RawProjectMemoryUnit, SourceLocation


class FilesystemUnitSource:
    def __init__(self, config: GroundedConfig) -> None:
        self._config = config

    def read_units(self) -> UnitSourceResult:
        specs_dir = self._config.specs_dir
        if not specs_dir.exists():
            return UnitSourceResult(
                (),
                (
                    ProjectMemoryIssue(
                        "GROUNDED-SPECS-001",
                        "specs directory does not exist",
                        SourceLocation.from_path(specs_dir),
                    ),
                ),
            )

        units: list[RawProjectMemoryUnit] = []
        issues: list[ProjectMemoryIssue] = []
        for path in sorted(specs_dir.rglob("*.json")):
            location = SourceLocation.from_path(path)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-JSON-001",
                        f"invalid JSON: {exc}",
                        location,
                    )
                )
                continue
            if not isinstance(data, dict):
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-SCHEMA-001",
                        "spec root must be a JSON object",
                        location,
                    )
                )
                continue
            units.append(RawProjectMemoryUnit(data=data, source_location=location))
        return UnitSourceResult(tuple(units), tuple(issues))
