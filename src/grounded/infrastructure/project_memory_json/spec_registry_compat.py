from __future__ import annotations

from ...models import Issue, Spec
from ...modules.project_memory.domain.issues import ProjectMemoryIssue
from ...modules.project_memory.domain.model import (
    ProjectMemory,
    ProjectMemoryType,
    TagTypeDefinition,
)


TypeDefinition = ProjectMemoryType


class SpecRegistry:
    def __init__(
        self,
        specs: list[Spec],
        issues: list[Issue],
        type_defs: dict[str, TypeDefinition],
        tag_type_defs: dict[str, TagTypeDefinition] | None = None,
    ) -> None:
        self.specs = specs
        self.issues = issues
        self.type_defs = type_defs
        self.tag_type_defs = tag_type_defs or {}
        self.by_id = {spec.id: spec for spec in specs}

    @property
    def active_specs(self) -> list[Spec]:
        return [spec for spec in self.specs if spec.status != "retired"]

    def get(self, spec_id: str) -> Spec | None:
        return self.by_id.get(spec_id)

    def type_definition_for(self, spec: Spec) -> TypeDefinition | None:
        return self.type_defs.get(spec.kind)


def spec_registry_from_project_memory(project_memory: ProjectMemory) -> SpecRegistry:
    specs: list[Spec] = []
    issues = [_compat_issue(issue) for issue in project_memory.issues]
    for unit in project_memory.units:
        if unit.source_location.path is None:
            issues.append(
                Issue(
                    "GROUNDED-COMPAT-001",
                    (
                        f"cannot convert unit {unit.id} to SpecRegistry: "
                        f"source location {unit.source_location.label!r} "
                        "has no filesystem path"
                    ),
                    None,
                    "error",
                )
            )
            continue
        specs.append(
            Spec(
                id=unit.id,
                kind=unit.kind,
                path=unit.source_location.path,
                data=unit.data,
            )
        )

    return SpecRegistry(
        specs,
        issues,
        dict(project_memory.types.definitions),
        dict(project_memory.types.tag_type_definitions),
    )


def _compat_issue(issue: object) -> Issue:
    if isinstance(issue, Issue):
        return issue
    if isinstance(issue, ProjectMemoryIssue):
        path = issue.source_location.path if issue.source_location is not None else None
        return Issue(issue.code, issue.message, path, issue.severity)
    raise TypeError(f"unsupported project memory issue: {issue!r}")
