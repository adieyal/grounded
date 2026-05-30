from __future__ import annotations

from collections import defaultdict

from ...edges import normalized_edges_for_units
from ...models import Issue, Spec
from ...modules.project_memory.domain.issues import ProjectMemoryIssue
from ...modules.project_memory.domain.model import (
    NormalizedEdge,
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
        normalized_edges: tuple[NormalizedEdge, ...] = (),
    ) -> None:
        self.specs = specs
        self.issues = issues
        self.type_defs = type_defs
        self.tag_type_defs = tag_type_defs or {}
        self.by_id = {spec.id: spec for spec in specs}
        self.normalized_edges = normalized_edges or normalized_edges_for_units(specs)
        outgoing_edges: dict[str, list[NormalizedEdge]] = defaultdict(list)
        incoming_edges: dict[str, list[NormalizedEdge]] = defaultdict(list)
        for edge in self.normalized_edges:
            outgoing_edges[edge.source_id].append(edge)
            incoming_edges[edge.target_id].append(edge)
        self._outgoing_edges_by_id = {
            spec.id: tuple(
                sorted(
                    outgoing_edges.get(spec.id, ()),
                    key=lambda edge: (
                        edge.edge_type,
                        edge.target_id,
                        edge.source_field or "",
                        edge.authored,
                    ),
                )
            )
            for spec in specs
        }
        self._incoming_edges_by_id = {
            spec.id: tuple(
                sorted(
                    incoming_edges.get(spec.id, ()),
                    key=lambda edge: (
                        edge.edge_type,
                        edge.source_id,
                        edge.source_field or "",
                        edge.authored,
                    ),
                )
            )
            for spec in specs
        }

    @property
    def active_specs(self) -> list[Spec]:
        return [spec for spec in self.specs if spec.status != "retired"]

    def get(self, spec_id: str) -> Spec | None:
        return self.by_id.get(spec_id)

    def type_definition_for(self, spec: Spec) -> TypeDefinition | None:
        return self.type_defs.get(spec.kind)

    def outgoing_edges_for(self, spec_id: str) -> tuple[NormalizedEdge, ...]:
        return self._outgoing_edges_by_id.get(spec_id, ())

    def incoming_edges_for(self, spec_id: str) -> tuple[NormalizedEdge, ...]:
        return self._incoming_edges_by_id.get(spec_id, ())


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
        project_memory.normalized_edges,
    )


def _compat_issue(issue: object) -> Issue:
    if isinstance(issue, Issue):
        return issue
    if isinstance(issue, ProjectMemoryIssue):
        path = issue.source_location.path if issue.source_location is not None else None
        return Issue(issue.code, issue.message, path, issue.severity)
    raise TypeError(f"unsupported project memory issue: {issue!r}")
