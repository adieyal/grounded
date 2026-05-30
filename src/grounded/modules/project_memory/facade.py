from __future__ import annotations

from pathlib import Path

from .application.load_project_memory import load_project_memory
from .application.ports import ShapeValidator, TypeSource, UnitSource
from .domain.model import ProjectMemory


class ProjectMemoryFacade:
    def __init__(
        self,
        unit_source: UnitSource,
        type_source: TypeSource,
        shape_validator: ShapeValidator,
        *,
        project_root: Path | None = None,
    ) -> None:
        self._unit_source = unit_source
        self._type_source = type_source
        self._shape_validator = shape_validator
        self._project_root = project_root

    def load(self) -> ProjectMemory:
        return load_project_memory(
            self._unit_source,
            self._type_source,
            self._shape_validator,
            project_root=self._project_root,
        )
