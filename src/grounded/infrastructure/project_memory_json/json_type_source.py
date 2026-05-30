from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ...models import GroundedConfig
from ...tags import TAG_SCHEMA
from ...trust_policy import TRUST_STATUSES
from ...modules.project_memory.application.ports import TypeSourceResult
from ...modules.project_memory.domain.issues import ProjectMemoryIssue
from ...modules.project_memory.domain.model import (
    ProjectMemoryType,
    ProjectMemoryTypes,
    ReferenceTagConstraint,
    SourceLocation,
    TagRequirement,
    TagTypeDefinition,
)


REGISTRY_UNIT_REQUIRED_FIELDS = ("id", "name", "status")
DOCUMENTED_REQUIRED_FIELDS = (
    "id",
    "name",
    "owner",
    "status",
    "description",
)
BASE_LINK_FIELDS = ("references", "tests", "examples")
TRUST_STATUS_SCHEMA = {
    "type": "string",
    "enum": [*TRUST_STATUSES],
}


DEFAULT_TYPE_REGISTRY: dict[str, dict[str, object]] = {
    "registry_unit": {
        "extends": None,
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": [*REGISTRY_UNIT_REQUIRED_FIELDS],
            "anyOf": [{"required": ["type"]}, {"required": ["kind"]}],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "type": {"type": "string", "minLength": 1},
                "kind": {"type": "string", "minLength": 1},
                "name": {"type": "string", "minLength": 1},
                "owner": {"type": "string", "minLength": 1},
                "status": {"type": "string", "enum": ["active", "draft", "retired"]},
                "summary": {"type": "string"},
                "trust_status": TRUST_STATUS_SCHEMA,
                "trust_basis": {"type": "string", "minLength": 1},
                "observed_basis": {"type": "string", "minLength": 1},
                "evidence": {"type": "string", "minLength": 1},
                "verification_refs": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "required": [*REGISTRY_UNIT_REQUIRED_FIELDS],
        "search_fields": ["id", "name", "summary"],
        "reference_fields": [],
        "semantic_category": "registry_infrastructure",
    },
    "knowledge_unit": {
        "extends": "registry_unit",
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["description"],
            "properties": {
                "description": {"type": "string", "minLength": 1},
                "tags": {
                    "type": "array",
                    "items": TAG_SCHEMA,
                    "uniqueItems": True,
                },
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "required": [*DOCUMENTED_REQUIRED_FIELDS],
        "search_fields": ["id", "name", "summary", "description"],
        "reference_fields": [],
        "semantic_category": "registry_infrastructure",
    },
    "domain_object": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*DOCUMENTED_REQUIRED_FIELDS],
            "properties": {
                "type": {"const": "domain_object"},
                "kind": {"const": "domain_object"},
                "definition": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "domain_object.html.j2",
        "required": [*DOCUMENTED_REQUIRED_FIELDS],
        "search_fields": ["id", "name", "definition", "summary", "description"],
        "reference_fields": [*BASE_LINK_FIELDS, "verification_refs"],
        "list_fields": ["verification_refs"],
        "semantic_category": "authored_knowledge",
    },
    "enum": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*DOCUMENTED_REQUIRED_FIELDS, "values"],
            "properties": {
                "type": {"const": "enum"},
                "kind": {"const": "enum"},
                "definition": {"type": "string"},
                "values": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
            },
            "additionalProperties": True,
        },
        "renderer": "enum.html.j2",
        "required": [*DOCUMENTED_REQUIRED_FIELDS],
        "search_fields": [
            "id",
            "name",
            "values",
            "definition",
            "summary",
            "description",
        ],
        "reference_fields": [*BASE_LINK_FIELDS, "verification_refs"],
        "list_fields": ["verification_refs"],
        "semantic_category": "authored_knowledge",
    },
    "verification": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*DOCUMENTED_REQUIRED_FIELDS, "target", "command"],
            "properties": {
                "type": {"const": "verification"},
                "kind": {"const": "verification"},
                "target": {"type": "string", "minLength": 1},
                "command": {"type": "string", "minLength": 1},
                "test_refs": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": True,
        },
        "renderer": "verification.html.j2",
        "required": [*DOCUMENTED_REQUIRED_FIELDS, "target", "command"],
        "search_fields": ["id", "name", "target", "command", "summary", "description"],
        "reference_fields": ["references"],
        "single_reference_fields": ["target"],
        "verification_fields": ["command"],
        "semantic_category": "registry_infrastructure",
    },
    "schema_gap": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*DOCUMENTED_REQUIRED_FIELDS, "gap", "suggested_improvement"],
            "properties": {
                "type": {"const": "schema_gap"},
                "kind": {"const": "schema_gap"},
                "gap": {"type": "string", "minLength": 1},
                "suggested_improvement": {"type": "string", "minLength": 1},
            },
            "additionalProperties": True,
        },
        "renderer": "schema_gap.html.j2",
        "required": [
            *DOCUMENTED_REQUIRED_FIELDS,
            "gap",
            "suggested_improvement",
        ],
        "search_fields": [
            "id",
            "name",
            "gap",
            "suggested_improvement",
            "summary",
            "description",
        ],
        "reference_fields": [*BASE_LINK_FIELDS, "verification_refs"],
        "list_fields": ["verification_refs"],
        "semantic_category": "registry_infrastructure",
    },
    "slice": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*DOCUMENTED_REQUIRED_FIELDS, "members"],
            "properties": {
                "type": {"const": "slice"},
                "kind": {"const": "slice"},
                "description": {"type": "string", "minLength": 1},
                "slug": {"type": "string", "minLength": 1},
                "members": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
                "index_template": {"type": "string", "minLength": 1},
                "style_path": {"type": "string", "minLength": 1},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "required": [*DOCUMENTED_REQUIRED_FIELDS],
        "search_fields": ["id", "name", "description", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS, "members"],
        "list_fields": ["members"],
        "semantic_category": "registry_infrastructure",
    },
    "generated_document": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [
                *DOCUMENTED_REQUIRED_FIELDS,
                "output_path",
                "format",
                "purpose",
                "section_refs",
            ],
            "properties": {
                "type": {"const": "generated_document"},
                "kind": {"const": "generated_document"},
                "output_path": {"type": "string", "minLength": 1},
                "format": {"type": "string", "enum": ["markdown"]},
                "write_mode": {
                    "type": "string",
                    "enum": ["protected_block", "full_file"],
                },
                "audience": {"type": "string", "minLength": 1},
                "purpose": {"type": "string", "minLength": 1},
                "stability": {
                    "type": "string",
                    "enum": ["experimental", "stable", "retired"],
                },
                "section_refs": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
                "source_refs": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
            },
            "additionalProperties": True,
        },
        "renderer": "generated_document.html.j2",
        "required": [
            *DOCUMENTED_REQUIRED_FIELDS,
            "output_path",
            "format",
            "purpose",
        ],
        "search_fields": [
            "id",
            "name",
            "output_path",
            "write_mode",
            "purpose",
            "summary",
            "description",
        ],
        "reference_fields": [*BASE_LINK_FIELDS, "section_refs", "source_refs"],
        "list_fields": ["section_refs", "source_refs"],
        "semantic_category": "generated_artifact",
    },
    "document_section": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [
                *DOCUMENTED_REQUIRED_FIELDS,
                "heading",
                "heading_level",
                "order",
                "renderer",
                "content_mode",
                "source_refs",
            ],
            "properties": {
                "type": {"const": "document_section"},
                "kind": {"const": "document_section"},
                "heading": {"type": "string", "minLength": 1},
                "heading_level": {"type": "integer", "minimum": 1, "maximum": 6},
                "order": {"type": "integer", "minimum": 0},
                "renderer": {
                    "type": "string",
                    "enum": [
                        "adoption_ladder",
                        "asset_figure",
                        "bullet_list",
                        "command_table",
                        "doc_link_list",
                        "json_example",
                        "ordered_steps",
                        "project_layout",
                        "source_summary",
                        "source_list",
                    ],
                },
                "content_mode": {
                    "type": "string",
                    "enum": ["sourced", "local_prose", "mixed"],
                },
                "source_refs": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
                "asset_refs": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
                "intro": {"type": "string"},
                "outro": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "document_section.html.j2",
        "required": [
            *DOCUMENTED_REQUIRED_FIELDS,
            "heading",
            "renderer",
            "content_mode",
        ],
        "search_fields": [
            "id",
            "name",
            "heading",
            "intro",
            "outro",
            "summary",
            "description",
        ],
        "reference_fields": [*BASE_LINK_FIELDS, "source_refs", "asset_refs"],
        "list_fields": ["source_refs", "asset_refs"],
        "semantic_category": "generated_artifact",
    },
    "documentation_set": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [
                *DOCUMENTED_REQUIRED_FIELDS,
                "default_output_dir",
                "document_refs",
            ],
            "properties": {
                "type": {"const": "documentation_set"},
                "kind": {"const": "documentation_set"},
                "default_output_dir": {"type": "string", "minLength": 1},
                "document_refs": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
            },
            "additionalProperties": True,
        },
        "renderer": "documentation_set.html.j2",
        "required": [*DOCUMENTED_REQUIRED_FIELDS, "default_output_dir"],
        "search_fields": ["id", "name", "summary", "description"],
        "reference_fields": [*BASE_LINK_FIELDS, "document_refs"],
        "list_fields": ["document_refs"],
        "semantic_category": "generated_artifact",
    },
    "asset": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [
                *DOCUMENTED_REQUIRED_FIELDS,
                "asset_kind",
                "path",
                "media_type",
            ],
            "properties": {
                "type": {"const": "asset"},
                "kind": {"const": "asset"},
                "asset_kind": {
                    "type": "string",
                    "enum": ["source_asset", "generated_asset", "external_asset"],
                },
                "path": {"type": "string", "minLength": 1},
                "media_type": {"type": "string", "minLength": 1},
                "alt": {"type": "string"},
                "decorative": {"type": "boolean"},
                "used_by": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
            },
            "additionalProperties": True,
            "anyOf": [
                {"required": ["alt"]},
                {
                    "properties": {"decorative": {"const": True}},
                    "required": ["decorative"],
                },
            ],
        },
        "renderer": "asset.html.j2",
        "required": [
            *DOCUMENTED_REQUIRED_FIELDS,
            "asset_kind",
            "path",
            "media_type",
        ],
        "search_fields": ["id", "name", "path", "alt", "summary", "description"],
        "reference_fields": [*BASE_LINK_FIELDS, "used_by"],
        "list_fields": ["used_by"],
        "semantic_category": "generated_artifact",
    },
}


class JsonTypeSource:
    def __init__(self, config: GroundedConfig) -> None:
        self._config = config

    def read_types(self) -> TypeSourceResult:
        issues: list[ProjectMemoryIssue] = []
        raw: dict[str, object] = DEFAULT_TYPE_REGISTRY
        registry_path = self._config.type_registry_path
        registry_location = SourceLocation.from_path(registry_path)

        if registry_path.exists():
            try:
                loaded = json.loads(registry_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-TYPE-001",
                        f"invalid type registry JSON: {exc}",
                        registry_location,
                    )
                )
                loaded = {}
            if isinstance(loaded, dict):
                raw = _merge_type_registry(DEFAULT_TYPE_REGISTRY, loaded)
            else:
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-TYPE-002",
                        "type registry root must be a JSON object",
                        registry_location,
                    )
                )
                raw = {}

        tag_type_defs, tag_type_issues = _load_tag_type_definitions(
            raw.get("tag_types"), registry_location
        )
        issues.extend(tag_type_issues)
        definitions: dict[str, ProjectMemoryType] = {}
        for type_name, value in raw.items():
            if type_name == "tag_types":
                continue
            if not isinstance(type_name, str) or not type_name:
                continue
            if not isinstance(value, dict):
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-TYPE-003",
                        f"type definition for {type_name} must be an object",
                        registry_location,
                    )
                )
                continue

            schema, schema_path, schema_issues = _load_schema(
                type_name, value, self._config
            )
            issues.extend(schema_issues)
            definitions[type_name] = ProjectMemoryType(
                type=type_name,
                extends=_optional_string(value.get("extends")),
                schema=schema,
                schema_path=schema_path,
                renderer=_string_value(value.get("renderer"), "unit.html.j2"),
                search_fields=_string_tuple(
                    value.get("search_fields", ("id", "name", "summary", "description"))
                ),
                verification_fields=_string_tuple(value.get("verification_fields", ())),
                reference_fields=_string_tuple(value.get("reference_fields", ())),
                single_reference_fields=_string_tuple(
                    value.get("single_reference_fields", ())
                ),
                nested_reference_fields=_nested_reference_paths(
                    value.get("nested_reference_fields", ())
                ),
                reference_tag_constraints=_reference_tag_constraints(
                    value.get("reference_tag_constraints", ())
                ),
                required=_string_tuple(value.get("required", ())),
                list_fields=_string_tuple(value.get("list_fields", ())),
                semantic_category=_semantic_category(value.get("semantic_category")),
            )

        return TypeSourceResult(
            ProjectMemoryTypes(definitions, tag_type_defs, registry_location),
            tuple(issues),
        )


def _merge_type_registry(
    defaults: dict[str, dict[str, object]], loaded: dict[str, object]
) -> dict[str, object]:
    merged: dict[str, object] = {key: dict(value) for key, value in defaults.items()}
    for type_name, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(type_name), dict):
            base = dict(merged[type_name])
            base.update(value)
            merged[type_name] = base
        else:
            merged[type_name] = value
    return merged


def _load_schema(
    type_name: str, value: dict[str, object], config: GroundedConfig
) -> tuple[dict[str, Any] | None, str | None, list[ProjectMemoryIssue]]:
    issues: list[ProjectMemoryIssue] = []
    schema_value = value.get("schema")
    schema_path = _optional_string(value.get("schema_path"))
    schema: dict[str, Any] | None = None
    registry_location = SourceLocation.from_path(config.type_registry_path)
    if isinstance(schema_value, dict):
        schema = schema_value
    elif schema_path:
        path = config.root / schema_path
        if not path.exists():
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TYPE-005",
                    f"type {type_name} schema_path does not exist: {schema_path}",
                    registry_location,
                )
            )
        else:
            location = SourceLocation.from_path(path)
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                issues.append(
                    ProjectMemoryIssue(
                        "GROUNDED-TYPE-006",
                        f"type {type_name} schema_path contains invalid JSON: {exc}",
                        location,
                    )
                )
            else:
                if isinstance(loaded, dict):
                    schema = loaded
                else:
                    issues.append(
                        ProjectMemoryIssue(
                            "GROUNDED-TYPE-007",
                            f"type {type_name} schema root must be an object",
                            location,
                        )
                    )
    if schema is not None:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TYPE-008",
                    f"type {type_name} JSON Schema is invalid: {exc.message}",
                    registry_location,
                )
            )
    return schema, schema_path, issues


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _semantic_category(value: object) -> str | None:
    category = _optional_string(value)
    if category is not None:
        return category
    return None


def _string_value(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _nested_reference_paths(value: object) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list | tuple):
        return ()
    paths: list[tuple[str, ...]] = []
    for item in value:
        if isinstance(item, str) and item:
            parts = tuple(part for part in item.split(".") if part)
            if parts:
                paths.append(parts)
        elif isinstance(item, list | tuple):
            parts = tuple(part for part in item if isinstance(part, str) and part)
            if parts:
                paths.append(parts)
    return tuple(paths)


def _reference_tag_constraints(value: object) -> tuple[ReferenceTagConstraint, ...]:
    if not isinstance(value, dict):
        return ()
    constraints: list[ReferenceTagConstraint] = []
    for raw_path, raw_requirement in value.items():
        if isinstance(raw_path, str):
            path = tuple(part for part in raw_path.split(".") if part)
        elif isinstance(raw_path, list | tuple):
            path = tuple(part for part in raw_path if isinstance(part, str) and part)
        else:
            path = ()
        if not path or not isinstance(raw_requirement, dict):
            continue
        tag_type = raw_requirement.get("type")
        tag_value = raw_requirement.get("value")
        if not isinstance(tag_type, str) or not isinstance(tag_value, str):
            continue
        if not tag_type or not tag_value:
            continue
        constraints.append(
            ReferenceTagConstraint(
                path=path,
                requires=TagRequirement(type=tag_type, value=tag_value),
            )
        )
    return tuple(constraints)


def _load_tag_type_definitions(
    value: object, location: SourceLocation
) -> tuple[dict[str, TagTypeDefinition], list[ProjectMemoryIssue]]:
    if value is None:
        return {}, []
    issues: list[ProjectMemoryIssue] = []
    definitions: dict[str, TagTypeDefinition] = {}
    if not isinstance(value, dict):
        return (
            {},
            [
                ProjectMemoryIssue(
                    "GROUNDED-TYPE-009",
                    "tag_types must be an object when present",
                    location,
                )
            ],
        )
    for tag_type, raw_definition in value.items():
        if not isinstance(tag_type, str) or not tag_type:
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TYPE-009",
                    "tag type names must be non-empty strings",
                    location,
                )
            )
            continue
        if raw_definition is None:
            raw_definition = {}
        if not isinstance(raw_definition, dict):
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-TYPE-009",
                    f"tag type {tag_type} definition must be an object",
                    location,
                )
            )
            continue
        definitions[tag_type] = TagTypeDefinition(
            type=tag_type,
            values=_string_tuple(raw_definition.get("values", ())),
            description=_optional_string(raw_definition.get("description")),
        )
    return definitions, issues
