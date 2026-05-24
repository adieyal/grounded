from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .models import Issue, LatticeConfig, Spec


BASE_REQUIRED_FIELDS = ("id", "name", "owner", "status")
BASE_LINK_FIELDS = ("references", "tests", "examples")


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
                "description": {"type": "string"},
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
                "preferred_term": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "domain_object.html.j2",
        "search_fields": ["id", "name", "preferred_term", "definition", "summary"],
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
        "search_fields": ["id", "name", "target", "command", "summary"],
        "reference_fields": ["references"],
        "single_reference_fields": ["target"],
        "verification_fields": ["command"],
    },
    "test_binding": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "target", "test"],
            "properties": {
                "type": {"const": "test_binding"},
                "kind": {"const": "test_binding"},
                "target": {"type": "string", "minLength": 1},
                "test": {"type": "string", "minLength": 1},
            },
            "additionalProperties": True,
        },
        "renderer": "verification.html.j2",
        "search_fields": ["id", "name", "target", "test", "summary"],
        "reference_fields": ["references"],
        "single_reference_fields": ["target"],
        "verification_fields": ["test"],
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
        "search_fields": ["id", "name", "gap", "suggested_improvement", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "concept": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "properties": {"type": {"const": "concept"}, "kind": {"const": "concept"}},
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "summary", "description"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "decision": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "decision"],
            "properties": {
                "type": {"const": "decision"},
                "kind": {"const": "decision"},
                "decision": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "decision", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "business_rule": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "statement"],
            "properties": {
                "type": {"const": "business_rule"},
                "kind": {"const": "business_rule"},
                "statement": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "statement", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "example": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "rule"],
            "properties": {
                "type": {"const": "example"},
                "kind": {"const": "example"},
                "rule": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "intent", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
        "single_reference_fields": ["rule"],
    },
    "guardrail": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "summary"],
            "properties": {
                "type": {"const": "guardrail"},
                "kind": {"const": "guardrail"},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "spec_type": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "definition"],
            "properties": {
                "type": {"const": "spec_type"},
                "kind": {"const": "spec_type"},
                "definition": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "definition", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "data_type": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "definition"],
            "properties": {
                "type": {"const": "data_type"},
                "kind": {"const": "data_type"},
                "definition": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "definition", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "workflow": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "summary"],
            "properties": {
                "type": {"const": "workflow"},
                "kind": {"const": "workflow"},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
    "lifecycle_value": {
        "extends": "knowledge_unit",
        "schema": {
            "type": "object",
            "required": [*BASE_REQUIRED_FIELDS, "summary"],
            "properties": {
                "type": {"const": "lifecycle_value"},
                "kind": {"const": "lifecycle_value"},
            },
            "additionalProperties": True,
        },
        "renderer": "unit.html.j2",
        "search_fields": ["id", "name", "summary"],
        "reference_fields": [*BASE_LINK_FIELDS],
    },
}


class SpecRegistry:
    def __init__(
        self,
        specs: list[Spec],
        issues: list[Issue],
        type_defs: dict[str, TypeDefinition],
    ) -> None:
        self.specs = specs
        self.issues = issues
        self.type_defs = type_defs
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
    type_defs, type_issues = load_type_registry(config)
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
        issues.extend(_validate_shape(spec, path, type_defs))

    registry = SpecRegistry(specs, issues, type_defs)
    issues.extend(_validate_references(registry))
    return registry


def default_type_registry_json() -> str:
    return json.dumps(DEFAULT_TYPE_REGISTRY, indent=2, sort_keys=True) + "\n"


def load_type_registry(
    config: LatticeConfig,
) -> tuple[dict[str, TypeDefinition], list[Issue]]:
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

    definitions: dict[str, TypeDefinition] = {}
    for type_name, value in raw.items():
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
                value.get("search_fields", ("id", "name", "summary"))
            ),
            verification_fields=_string_tuple(value.get("verification_fields", ())),
            reference_fields=_string_tuple(
                value.get("reference_fields", ("references",))
            ),
            single_reference_fields=_string_tuple(
                value.get("single_reference_fields", ())
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
    return definitions, issues


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


def _validate_shape(
    spec: Spec, path: Path, type_defs: dict[str, TypeDefinition]
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
    return issues
