from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..domain.issues import ProjectMemoryIssue
from ..domain.model import (
    ProjectMemoryTypes,
    RawProjectMemoryUnit,
)


@dataclass(frozen=True)
class UnitSourceResult:
    units: tuple[RawProjectMemoryUnit, ...]
    issues: tuple[ProjectMemoryIssue, ...] = ()


@dataclass(frozen=True)
class TypeSourceResult:
    types: ProjectMemoryTypes
    issues: tuple[ProjectMemoryIssue, ...] = ()


class UnitSource(Protocol):
    def read_units(self) -> UnitSourceResult:
        pass


class TypeSource(Protocol):
    def read_types(self) -> TypeSourceResult:
        pass


class ShapeValidator(Protocol):
    def validate(
        self,
        unit: RawProjectMemoryUnit,
        types: ProjectMemoryTypes,
    ) -> list[ProjectMemoryIssue]:
        pass
