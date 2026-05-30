from __future__ import annotations

import json

from .infrastructure.project_memory_json import (
    DEFAULT_TYPE_REGISTRY,
    FilesystemUnitSource,
    JsonProjectMemoryShapeValidator,
    JsonTypeSource,
    SpecRegistry,
    spec_registry_from_project_memory,
)
from .infrastructure.project_memory_json.spec_registry_compat import (
    TypeDefinition,
)
from .models import Issue, GroundedConfig
from .modules.project_memory import (
    ProjectMemoryFacade,
    ReferenceTagConstraint,
    TagRequirement,
    TagTypeDefinition,
    ProjectMemoryIssue,
    validate_type_definitions,
)


def load_registry(config: GroundedConfig) -> SpecRegistry:
    facade = ProjectMemoryFacade(
        FilesystemUnitSource(config),
        JsonTypeSource(config),
        JsonProjectMemoryShapeValidator(),
        project_root=config.root,
    )
    return spec_registry_from_project_memory(facade.load())


def default_type_registry_json() -> str:
    return json.dumps(DEFAULT_TYPE_REGISTRY, indent=2, sort_keys=True) + "\n"


def load_type_registry(
    config: GroundedConfig,
) -> tuple[dict[str, TypeDefinition], dict[str, TagTypeDefinition], list[Issue]]:
    result = JsonTypeSource(config).read_types()
    issues = [
        *result.issues,
        *validate_type_definitions(result.types),
    ]
    return (
        dict(result.types.definitions),
        dict(result.types.tag_type_definitions),
        [_compat_issue(issue) for issue in issues],
    )


def _compat_issue(issue: ProjectMemoryIssue) -> Issue:
    path = issue.source_location.path if issue.source_location is not None else None
    return Issue(issue.code, issue.message, path, issue.severity)


__all__ = [
    "DEFAULT_TYPE_REGISTRY",
    "ReferenceTagConstraint",
    "SpecRegistry",
    "TagRequirement",
    "TagTypeDefinition",
    "TypeDefinition",
    "default_type_registry_json",
    "load_registry",
    "load_type_registry",
]
