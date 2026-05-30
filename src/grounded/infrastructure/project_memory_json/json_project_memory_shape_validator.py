from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

from ...modules.project_memory.application.shape_validation import (
    validate_project_memory_shape,
)
from ...modules.project_memory.domain.issues import ProjectMemoryIssue
from ...modules.project_memory.domain.model import (
    ProjectMemoryTypes,
    RawProjectMemoryUnit,
)


class JsonProjectMemoryShapeValidator:
    def validate(
        self,
        unit: RawProjectMemoryUnit,
        types: ProjectMemoryTypes,
    ) -> list[ProjectMemoryIssue]:
        data = dict(unit.data)
        issues = validate_project_memory_shape(unit, types)
        kind = _spec_type(data)
        type_def = types.get(kind) if kind is not None else None
        if type_def is None:
            return issues

        for parent in types.schema_chain(type_def):
            if parent.schema is None:
                continue
            validator = Draft202012Validator(parent.schema)
            for error in sorted(validator.iter_errors(data), key=str):
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-SCHEMA-006",
                        f"{parent.type} schema: {_format_schema_error(error)}",
                        unit.source_location,
                    )
                )
        return issues


def _spec_type(data: dict[str, Any]) -> str | None:
    return _string_field(data, "type") or _string_field(data, "kind")


def _string_field(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _format_schema_error(error: Any) -> str:
    location = ".".join(str(part) for part in error.absolute_path)
    prefix = f"{location}: " if location else ""
    return f"{prefix}{error.message}"
