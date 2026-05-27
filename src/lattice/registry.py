from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .models import Issue, LatticeConfig, Spec
from .rich_text import rich_text_reference_ids
from .tags import TAG_SCHEMA, has_typed_tag, normalize_tag


BASE_REQUIRED_FIELDS = ("id", "name", "owner", "status", "description")
BASE_LINK_FIELDS = ("references", "tests", "examples")


@dataclass(frozen=True)
class TagTypeDefinition:
    type: str
    values: tuple[str, ...]
    description: str | None = None


@dataclass(frozen=True)
class TagRequirement:
    type: str
    value: str

    @property
    def label(self) -> str:
        return f"{self.type}:{self.value}"


@dataclass(frozen=True)
class ReferenceTagConstraint:
    path: tuple[str, ...]
    requires: TagRequirement


@dataclass(frozen=True)
class TypeDefinition:
    type: str
    extends: str | None
    schema: dict[str, Any] | None
    schema_path: str | None
    renderer: str
    search_fields: tuple[str, ...]
    verification_fields: tuple[str, ...]
    reference_fields: tuple[str, ...]
    single_reference_fields: tuple[str, ...]
    nested_reference_fields: tuple[tuple[str, ...], ...]
    reference_tag_constraints: tuple[ReferenceTagConstraint, ...]
    required: tuple[str, ...]
    list_fields: tuple[str, ...]

    @property
    def kind(self) -> str:
        return self.type


DEFAULT_TYPE_REGISTRY: dict[str, dict[str, object]] = {
    "knowledge_unit": {
        "extends": None,
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS],
            "anyOf": [{"required": ["type"]}, {"required": ["kind"]}],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "type": {"type": "string", "minLength": 1},
                "kind": {"type": "string", "minLength": 1},
                "name": {"type": "string", "minLength": 1},
                "owner": {"type": "string", "minLength": 1},
                "status": {"type": "string", "enum": ["active", "draft", "retired"]},
                "summary": {"type": "string"},
                "description": {"type": "string", "minLength": 1},
                "tags": {
                    "type": "array",
                    "items": TAG_SCHEMA,
                    "uniqueItems": True,
                },
                "references": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "tests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "examples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "links": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "required": ["target_id"],
                                "properties": {
                                    "target_id": {"type": "string", "minLength": 1},
                                    "target_type": {"type": "string", "minLength": 1},
                                    "relationship": {"type": "string", "minLength": 1},
                                },
                                "additionalProperties": True,
                            },
                        ]
                    },
                },
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "required": [*BASE_REQUIRED_FIELDS],
        "search_fields": ["id", "name", "summary", "description"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "domain_object": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS],
            "properties": {
                "type": {"const": "domain_object"},
                "kind": {"const": "domain_object"},
                "definition": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "domain_object.html.j2",
        "required": [*BASE_REQUIRED_FIELDS],
        "search_fields": ["id", "name", "definition", "summary", "description"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "enum": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "values"],
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
        "required": [*BASE_REQUIRED_FIELDS],
        "search_fields": [
            "id",
            "name",
            "values",
            "definition",
            "summary",
            "description",
        ],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "verification": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "target", "command"],
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
        "required": [*BASE_REQUIRED_FIELDS, "target", "command"],
        "search_fields": ["id", "name", "target", "command", "summary", "description"],
        "reference_fields": ["references"],
        "single_reference_fields": ["target"],
        "verification_fields": ["command"],
    },
    "schema_gap": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "gap", "suggested_improvement"],
            "properties": {
                "type": {"const": "schema_gap"},
                "kind": {"const": "schema_gap"},
                "gap": {"type": "string", "minLength": 1},
                "suggested_improvement": {"type": "string", "minLength": 1},
            },
            "additionalProperties": True,
        },
        "renderer": "schema_gap.html.j2",
        "required": [*BASE_REQUIRED_FIELDS, "gap", "suggested_improvement"],
        "search_fields": [
            "id",
            "name",
            "gap",
            "suggested_improvement",
            "summary",
            "description",
        ],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "slice": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "members"],
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
        "required": [*BASE_REQUIRED_FIELDS],
        "search_fields": ["id", "name", "description", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS, "members"],
        "list_fields": ["members"],
    },
}


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


def load_registry(config: LatticeConfig) -> SpecRegistry:
    issues: list[Issue] = []
    specs: list[Spec] = []
    seen: dict[str, Path] = {}
    type_defs, tag_type_defs, type_issues = load_type_registry(config)
    issues.extend(type_issues)

    if not config.specs_dir.exists():
        return SpecRegistry(
            [],
            [
                Issue(
                    "LATTICE-SPECS-001",
                    "specs directory does not exist",
                    config.specs_dir,
                )
            ],
            type_defs,
            tag_type_defs,
        )

    for path in sorted(config.specs_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(Issue("LATTICE-JSON-001", f"invalid JSON: {exc}", path))
            continue
        if not isinstance(data, dict):
            issues.append(
                Issue("LATTICE-SCHEMA-001", "spec root must be a JSON object", path)
            )
            continue

        spec_id = _string_field(data, "id")
        spec_type = _spec_type(data)
        if spec_id is None or spec_type is None:
            issues.append(
                Issue(
                    "LATTICE-SCHEMA-002",
                    "spec must contain string id and type or kind",
                    path,
                )
            )
            continue
        if spec_id in seen:
            issues.append(
                Issue(
                    "LATTICE-ID-001",
                    f"duplicate id {spec_id}; first defined at {seen[spec_id]}",
                    path,
                )
            )
            continue
        seen[spec_id] = path

        normalized = dict(data)
        normalized.setdefault("type", spec_type)
        normalized.setdefault("kind", spec_type)
        spec = Spec(id=spec_id, kind=spec_type, path=path, data=normalized)
        specs.append(spec)
        issues.extend(_validate_shape(spec, path, type_defs, tag_type_defs))

    registry = SpecRegistry(specs, issues, type_defs, tag_type_defs)
    issues.extend(_validate_references(registry))
    return registry


def default_type_registry_json() -> str:
    return json.dumps(DEFAULT_TYPE_REGISTRY, indent=2, sort_keys=True) + "\n"


def load_type_registry(
    config: LatticeConfig,
) -> tuple[dict[str, TypeDefinition], dict[str, TagTypeDefinition], list[Issue]]:
    issues: list[Issue] = []
    raw: dict[str, object] = DEFAULT_TYPE_REGISTRY
    if config.type_registry_path.exists():
        try:
            loaded = json.loads(config.type_registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                Issue(
                    "LATTICE-TYPE-001",
                    f"invalid type registry JSON: {exc}",
                    config.type_registry_path,
                )
            )
            loaded = {}
        if isinstance(loaded, dict):
            raw = _merge_type_registry(DEFAULT_TYPE_REGISTRY, loaded)
        else:
            issues.append(
                Issue(
                    "LATTICE-TYPE-002",
                    "type registry root must be a JSON object",
                    config.type_registry_path,
                )
            )
            raw = {}

    tag_type_defs, tag_type_issues = _load_tag_type_definitions(
        raw.get("tag_types"), config
    )
    issues.extend(tag_type_issues)
    definitions: dict[str, TypeDefinition] = {}
    for type_name, value in raw.items():
        if type_name == "tag_types":
            continue
        if not isinstance(type_name, str) or not type_name:
            continue
        if not isinstance(value, dict):
            issues.append(
                Issue(
                    "LATTICE-TYPE-003",
                    f"type definition for {type_name} must be an object",
                    config.type_registry_path,
                )
            )
            continue
        schema, schema_path, schema_issues = _load_schema(type_name, value, config)
        issues.extend(schema_issues)
        definitions[type_name] = TypeDefinition(
            type=type_name,
            extends=_optional_string(value.get("extends")),
            schema=schema,
            schema_path=schema_path,
            renderer=_string_value(value.get("renderer"), "unit.html.j2"),
            search_fields=_string_tuple(
                value.get("search_fields", ("id", "name", "summary", "description"))
            ),
            verification_fields=_string_tuple(value.get("verification_fields", ())),
            reference_fields=_string_tuple(
                value.get("reference_fields", ("references",))
            ),
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
        )

    for type_name, definition in definitions.items():
        if definition.extends is not None and definition.extends not in definitions:
            issues.append(
                Issue(
                    "LATTICE-TYPE-004",
                    f"type {type_name} extends unknown parent type {definition.extends}",
                    config.type_registry_path,
                )
            )
    issues.extend(
        _validate_reference_tag_constraint_definitions(
            definitions, tag_type_defs, config.type_registry_path
        )
    )
    return definitions, tag_type_defs, issues


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
    type_name: str, value: dict[str, object], config: LatticeConfig
) -> tuple[dict[str, Any] | None, str | None, list[Issue]]:
    issues: list[Issue] = []
    schema_value = value.get("schema")
    schema_path = _optional_string(value.get("schema_path"))
    schema: dict[str, Any] | None = None
    if isinstance(schema_value, dict):
        schema = schema_value
    elif schema_path:
        path = config.root / schema_path
        if not path.exists():
            issues.append(
                Issue(
                    "LATTICE-TYPE-005",
                    f"type {type_name} schema_path does not exist: {schema_path}",
                    config.type_registry_path,
                )
            )
        else:
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                issues.append(
                    Issue(
                        "LATTICE-TYPE-006",
                        f"type {type_name} schema_path contains invalid JSON: {exc}",
                        path,
                    )
                )
            else:
                if isinstance(loaded, dict):
                    schema = loaded
                else:
                    issues.append(
                        Issue(
                            "LATTICE-TYPE-007",
                            f"type {type_name} schema root must be an object",
                            path,
                        )
                    )
    if schema is not None:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            issues.append(
                Issue(
                    "LATTICE-TYPE-008",
                    f"type {type_name} JSON Schema is invalid: {exc.message}",
                    config.type_registry_path,
                )
            )
    return schema, schema_path, issues


def _spec_type(data: dict[str, Any]) -> str | None:
    return _string_field(data, "type") or _string_field(data, "kind")


def _string_field(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


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
    value: object, config: LatticeConfig
) -> tuple[dict[str, TagTypeDefinition], list[Issue]]:
    if value is None:
        return {}, []

    issues: list[Issue] = []
    definitions: dict[str, TagTypeDefinition] = {}
    if not isinstance(value, dict):
        return (
            {},
            [
                Issue(
                    "LATTICE-TYPE-009",
                    "tag_types must be an object when present",
                    config.type_registry_path,
                )
            ],
        )

    for tag_type, raw_definition in value.items():
        if not isinstance(tag_type, str) or not tag_type:
            issues.append(
                Issue(
                    "LATTICE-TYPE-009",
                    "tag type names must be non-empty strings",
                    config.type_registry_path,
                )
            )
            continue
        if raw_definition is None:
            raw_definition = {}
        if not isinstance(raw_definition, dict):
            issues.append(
                Issue(
                    "LATTICE-TYPE-009",
                    f"tag type {tag_type} definition must be an object",
                    config.type_registry_path,
                )
            )
            continue

        definitions[tag_type] = TagTypeDefinition(
            type=tag_type,
            values=_string_tuple(raw_definition.get("values", ())),
            description=_optional_string(raw_definition.get("description")),
        )
    return definitions, issues


def _validate_reference_tag_constraint_definitions(
    definitions: dict[str, TypeDefinition],
    tag_type_defs: dict[str, TagTypeDefinition],
    registry_path: Path,
) -> list[Issue]:
    issues: list[Issue] = []
    for type_name, definition in definitions.items():
        reference_paths = {(field,) for field in definition.reference_fields} | {
            (field,) for field in definition.single_reference_fields
        }
        reference_paths.update(definition.nested_reference_fields)
        for constraint in definition.reference_tag_constraints:
            if constraint.path not in reference_paths:
                issues.append(
                    Issue(
                        "LATTICE-TYPE-010",
                        f"type {type_name} constrains non-reference field {'.'.join(constraint.path)}",
                        registry_path,
                    )
                )
            issues.extend(
                _validate_tag_requirement_definition(
                    constraint.requires, tag_type_defs, registry_path
                )
            )
    return issues


def _validate_tag_requirement_definition(
    requirement: TagRequirement,
    tag_type_defs: dict[str, TagTypeDefinition],
    path: Path,
) -> list[Issue]:
    if not tag_type_defs:
        return []
    tag_def = tag_type_defs.get(requirement.type)
    if tag_def is None:
        return [
            Issue(
                "LATTICE-TAG-001",
                f"unknown tag type {requirement.type}",
                path,
            )
        ]
    if tag_def.values and requirement.value not in tag_def.values:
        return [
            Issue(
                "LATTICE-TAG-002",
                f"unknown value {requirement.value} for tag type {requirement.type}",
                path,
            )
        ]
    return []


def _validate_shape(
    spec: Spec,
    path: Path,
    type_defs: dict[str, TypeDefinition],
    tag_type_defs: dict[str, TagTypeDefinition],
) -> list[Issue]:
    issues: list[Issue] = []
    type_def = type_defs.get(spec.kind)
    if type_def is None:
        issues.append(
            Issue(
                "LATTICE-KIND-001",
                f"unknown spec type {spec.kind}; add it to the type registry or correct the spec",
                path,
            )
        )
        return issues

    for field in type_def.required:
        if not _string_field(spec.data, field):
            issues.append(
                Issue(
                    "LATTICE-SCHEMA-003",
                    f"missing required string field: {field}",
                    path,
                )
            )

    for list_field in type_def.list_fields:
        value = spec.data.get(list_field, [])
        if value is not None and not isinstance(value, list):
            issues.append(
                Issue(
                    "LATTICE-SCHEMA-004",
                    f"{list_field} must be a list when present",
                    path,
                )
            )

    for parent in _schema_chain(type_def, type_defs):
        if parent.schema is None:
            continue
        validator = Draft202012Validator(parent.schema)
        for error in sorted(validator.iter_errors(spec.data), key=str):
            issues.append(
                Issue(
                    "LATTICE-SCHEMA-006",
                    f"{parent.type} schema: {_format_schema_error(error)}",
                    path,
                )
            )
    issues.extend(_validate_tags(spec.data, (), path, tag_type_defs))
    return issues


def _validate_tags(
    value: object,
    path_parts: tuple[str, ...],
    path: Path,
    tag_type_defs: dict[str, TagTypeDefinition],
) -> list[Issue]:
    issues: list[Issue] = []
    if isinstance(value, dict):
        for key, item in value.items():
            current_path = (*path_parts, key)
            if key == "tags":
                issues.extend(
                    _validate_tag_list(item, current_path, path, tag_type_defs)
                )
            else:
                issues.extend(_validate_tags(item, current_path, path, tag_type_defs))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            issues.extend(
                _validate_tags(item, (*path_parts, str(index)), path, tag_type_defs)
            )
    return issues


def _validate_tag_list(
    value: object,
    path_parts: tuple[str, ...],
    path: Path,
    tag_type_defs: dict[str, TagTypeDefinition],
) -> list[Issue]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [
            Issue(
                "LATTICE-TAG-003",
                f"{'.'.join(path_parts)} must be a list when present",
                path,
            )
        ]

    issues: list[Issue] = []
    for item in value:
        tag = normalize_tag(item)
        if tag is None:
            issues.append(
                Issue(
                    "LATTICE-TAG-003",
                    f"{'.'.join(path_parts)} entries must be strings or typed tag objects",
                    path,
                )
            )
            continue
        if tag.type is not None:
            issues.extend(
                _validate_tag_requirement_definition(
                    TagRequirement(tag.type, tag.value), tag_type_defs, path
                )
            )
    return issues


def _schema_chain(
    type_def: TypeDefinition, type_defs: dict[str, TypeDefinition]
) -> tuple[TypeDefinition, ...]:
    chain: list[TypeDefinition] = []
    current: TypeDefinition | None = type_def
    while current is not None:
        chain.append(current)
        current = type_defs.get(current.extends) if current.extends else None
    return tuple(reversed(chain))


def _format_schema_error(error: Any) -> str:
    location = ".".join(str(part) for part in error.absolute_path)
    prefix = f"{location}: " if location else ""
    return f"{prefix}{error.message}"


def _validate_references(registry: SpecRegistry) -> list[Issue]:
    issues: list[Issue] = []
    for spec in registry.specs:
        type_def = registry.type_defs.get(spec.kind)
        reference_fields = type_def.reference_fields if type_def else ("references",)
        single_reference_fields = type_def.single_reference_fields if type_def else ()
        nested_reference_fields = type_def.nested_reference_fields if type_def else ()
        for field in reference_fields:
            value = spec.data.get(field, [])
            if not isinstance(value, list):
                continue
            for ref in value:
                if isinstance(ref, str) and ref not in registry.by_id:
                    issues.append(
                        Issue(
                            "LATTICE-REF-001",
                            f"{spec.id}.{field} references unknown spec {ref}",
                            spec.path,
                        )
                    )
        for field in single_reference_fields:
            value = spec.data.get(field)
            if isinstance(value, str) and value not in registry.by_id:
                issues.append(
                    Issue(
                        "LATTICE-REF-002",
                        f"{spec.id}.{field} points to unknown spec {value}",
                        spec.path,
                    )
                )
        for path in nested_reference_fields:
            for ref in _nested_values(spec.data, path):
                if isinstance(ref, str) and ref not in registry.by_id:
                    issues.append(
                        Issue(
                            "LATTICE-REF-001",
                            f"{spec.id}.{'.'.join(path)} references unknown spec {ref}",
                            spec.path,
                        )
                    )
                elif isinstance(ref, list):
                    for item in ref:
                        if isinstance(item, str) and item not in registry.by_id:
                            issues.append(
                                Issue(
                                    "LATTICE-REF-001",
                                    f"{spec.id}.{'.'.join(path)} references unknown spec {item}",
                                    spec.path,
                                )
                            )
        links = spec.data.get("links", [])
        if isinstance(links, list):
            for index, link in enumerate(links):
                target = (
                    link
                    if isinstance(link, str)
                    else link.get("target_id")
                    if isinstance(link, dict)
                    else None
                )
                if isinstance(target, str) and target not in registry.by_id:
                    issues.append(
                        Issue(
                            "LATTICE-REF-003",
                            f"{spec.id}.links[{index}] points to unknown spec {target}",
                            spec.path,
                        )
                    )
        for target in rich_text_reference_ids(spec.data):
            if target not in registry.by_id:
                issues.append(
                    Issue(
                        "LATTICE-REF-001",
                        f"{spec.id} inline rich-text link references unknown spec {target}",
                        spec.path,
                    )
                )
        if type_def is not None:
            issues.extend(_validate_reference_tag_constraints(spec, registry, type_def))
    return issues


def _validate_reference_tag_constraints(
    spec: Spec, registry: SpecRegistry, type_def: TypeDefinition
) -> list[Issue]:
    issues: list[Issue] = []
    for constraint in type_def.reference_tag_constraints:
        for ref in _reference_values_at_path(spec.data, constraint.path):
            target = registry.by_id.get(ref)
            if target is None:
                continue
            if has_typed_tag(
                target.data.get("tags", []),
                constraint.requires.type,
                constraint.requires.value,
            ):
                continue
            issues.append(
                Issue(
                    "LATTICE-REF-005",
                    f"{spec.id}.{'.'.join(constraint.path)} references {ref}, which is missing required tag {constraint.requires.label}",
                    spec.path,
                )
            )
    return issues


def _reference_values_at_path(
    data: dict[str, Any], path: tuple[str, ...]
) -> tuple[str, ...]:
    refs: list[str] = []
    for value in _nested_values(data, path):
        if isinstance(value, str):
            refs.append(value)
        elif isinstance(value, list):
            refs.extend(item for item in value if isinstance(item, str))
    return tuple(refs)


def _nested_values(data: object, path: tuple[str, ...]) -> list[object]:
    if not path:
        return [data]
    head, *tail = path
    rest = tuple(tail)
    if isinstance(data, dict):
        if head not in data:
            return []
        return _nested_values(data[head], rest)
    if isinstance(data, list):
        values: list[object] = []
        for item in data:
            values.extend(_nested_values(item, path))
        return values
    return []
