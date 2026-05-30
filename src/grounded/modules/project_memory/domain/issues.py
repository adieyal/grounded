from __future__ import annotations

from dataclasses import dataclass

from .model import SourceLocation


@dataclass(frozen=True)
class ProjectMemoryIssue:
    code: str
    message: str
    source_location: SourceLocation | None = None
    severity: str = "error"
