from __future__ import annotations

import json
from html import escape
from typing import Any

from .models import Spec
from .registry import SpecRegistry
from .render_paths import slugify
from .tags import tag_keys
from .trust_policy import TRUST_STATUS_DESCRIPTIONS


def grounded_link(
    type_name: object,
    unit_id: object,
    label: object | None = None,
    variant: str | None = None,
    fragment: object | None = None,
) -> str:
    variant_attr = f' variant="{escape(variant)}"' if variant else ""
    label_attr = f' label="{escape(str(label))}"' if label is not None else ""
    fragment_attr = (
        f' fragment="{escape(str(fragment))}"' if fragment is not None else ""
    )
    text = str(label) if label is not None else str(unit_id)
    return (
        f'<grounded-link type="{escape(str(type_name))}" grounded-id="{escape(str(unit_id))}"{label_attr}{fragment_attr}{variant_attr}>'
        f"{escape(text)}</grounded-link>"
    )


def field_label(value: str) -> str:
    return value.replace("_", " ").title()


TYPE_TONES = {
    "asset": "flow",
    "business_entity": "ent",
    "domain_object": "ent",
    "concept": "con",
    "decision": "con",
    "document_section": "flow",
    "documentation_set": "flow",
    "enum": "enu",
    "generated_document": "flow",
    "guardrail": "meta",
    "lifecycle_type": "enu",
    "lifecycle_value": "enu",
    "data_type": "type",
    "schema_gap": "meta",
    "test_binding": "meta",
    "verification": "meta",
    "workflow": "flow",
    "registry_type": "type",
    "spec_type": "type",
}


TYPE_NAV_LABELS = {
    "asset": "Assets",
    "business_entity": "Business Entities",
    "domain_object": "Domain",
    "concept": "Concepts",
    "decision": "Decisions",
    "document_section": "Generated Artifacts",
    "documentation_set": "Generated Artifacts",
    "enum": "Enums",
    "generated_document": "Generated Artifacts",
    "guardrail": "Guardrails",
    "lifecycle_type": "Lifecycle Types",
    "lifecycle_value": "Lifecycle Values",
    "data_type": "Data Types",
    "schema_gap": "Schema Gaps",
    "test_binding": "Test Bindings",
    "verification": "Verification",
    "workflow": "Workflows",
    "registry_type": "Grounded Types",
    "spec_type": "Grounded Types",
}

TYPE_LABELS = {
    "asset": "Generated Artifact",
    "document_section": "Generated Artifact",
    "documentation_set": "Generated Artifact",
    "generated_document": "Generated Artifact",
    "registry_type": "Registry Type",
    "spec_type": "Registry Type",
    "verification": "Verification",
}


def type_tone(type_name: object) -> str:
    return TYPE_TONES.get(str(type_name), "meta")


def type_nav_label(type_name: object) -> str:
    return TYPE_NAV_LABELS.get(str(type_name), field_label(str(type_name)))


def type_label(type_name: object) -> str:
    return TYPE_LABELS.get(str(type_name), field_label(str(type_name)))


def page_component(type_name: object) -> str:
    components = {
        "business_entity": "grounded-business-entity-page",
        "domain_object": "grounded-domain-object-page",
        "enum": "grounded-enum-page",
        "lifecycle_type": "grounded-lifecycle-type-page",
    }
    return components.get(str(type_name), "grounded-unit-page")


DETAIL_FIELD_EXCLUDES = {
    "asset_refs",
    "audience",
    "command",
    "content_mode",
    "default_output_dir",
    "document_refs",
    "id",
    "type",
    "kind",
    "name",
    "short_name",
    "tags",
    "owner",
    "status",
    "description",
    "references",
    "tests",
    "examples",
    "links",
    "fields",
    "format",
    "gap",
    "heading",
    "heading_level",
    "intro",
    "order",
    "outro",
    "output_path",
    "purpose",
    "renderer",
    "section_refs",
    "source_refs",
    "stability",
    "statement",
    "suggested_improvement",
    "target",
    "test",
    "used_by",
    "write_mode",
}


def display_fields(spec: Spec) -> list[dict[str, Any]]:
    fields = spec.data.get("fields")
    if isinstance(fields, list) and fields:
        rows: list[dict[str, Any]] = []
        for field in fields:
            if not isinstance(field, dict):
                continue

            allowed_values = field.get("allowed_values", [])
            if allowed_values is None:
                allowed_values = []
            elif not isinstance(allowed_values, list):
                allowed_values = [allowed_values]

            references = field.get("references", [])
            if references is None:
                references = []
            elif not isinstance(references, list):
                references = [references]

            tags = field.get("tags", [])
            if tags is None:
                tags = []
            elif not isinstance(tags, list):
                tags = [tags]

            rows.append(
                {
                    "name": str(field.get("name", "")),
                    "type": str(field.get("type", "value")),
                    "required": field.get("required"),
                    "description": display_value(field.get("description", "")),
                    "allowed_values": [
                        display_value(value) for value in allowed_values
                    ],
                    "tags": [
                        str(value)
                        for value in tag_keys(tags)
                        if isinstance(value, str) and value
                    ],
                    "references": [str(value) for value in references],
                }
            )

        if rows:
            return rows

    rows: list[dict[str, Any]] = []
    for key, value in spec.data.items():
        if key in DETAIL_FIELD_EXCLUDES or (spec.kind == "enum" and key == "values"):
            continue
        rows.append(
            {
                "name": key,
                "type": value_type_name(value),
                "required": key in {"definition", "summary", "statement", "decision"},
                "description": display_value(value),
                "allowed_values": [],
                "tags": [],
                "references": [],
            }
        )
    return rows


def field_type_display(field_type: object, registry: SpecRegistry) -> str:
    type_name = str(field_type)
    stripped_type_name, is_collection = _split_field_type(type_name)
    if stripped_type_name == "dict":
        return '<span class="pill field-type">dict</span>'

    target = field_type_target(stripped_type_name, registry)
    if target is None:
        rendered = escape(stripped_type_name)
        if is_collection:
            rendered = f"list[{rendered}]"
        return f'<span class="pill field-type">{rendered}</span>'

    rendered = grounded_link(target.kind, target.id, display_name(target), "field-type")
    if is_collection:
        return f"list[{rendered}]"
    return rendered


def display_name(spec: Spec) -> str:
    return spec.display_name


def enum_values(spec: Spec) -> list[str]:
    values = spec.data.get("values", [])
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str)]


def enum_value_descriptions(spec: Spec) -> list[dict[str, str]]:
    values = enum_values(spec)
    if spec.id != "GROUNDED-TRUST-STATUS-001":
        return [{"value": value, "description": ""} for value in values]
    return [
        {"value": value, "description": TRUST_STATUS_DESCRIPTIONS.get(value, "")}
        for value in values
    ]


def trust_status_detail(spec: Spec) -> dict[str, str] | None:
    value = spec.data.get("trust_status")
    if not isinstance(value, str) or not value:
        return None
    return {
        "value": value,
        "label": field_label(value),
        "description": TRUST_STATUS_DESCRIPTIONS.get(value, ""),
    }


def field_anchor(unit_id: object, field_name: object) -> str:
    return f"field-{slugify(unit_id)}-{slugify(field_name)}"


def field_type_target(type_name: str, registry: SpecRegistry) -> Spec | None:
    if type_name in registry.by_id:
        return registry.by_id[type_name]

    normalized_type = type_name.casefold()
    matches: list[Spec] = []

    for spec in registry.active_specs:
        candidate_names = [
            spec.id,
            spec.short_name or "",
            str(spec.data.get("name", "")),
        ]
        if any(
            candidate.casefold() == normalized_type for candidate in candidate_names
        ):
            matches.append(spec)

    if len(matches) == 1:
        return matches[0]

    return None


def _split_field_type(type_name: str) -> tuple[str, bool]:
    stripped = type_name.replace(" | None", "").replace("| None", "").strip()
    is_collection = stripped.startswith("list[") and stripped.endswith("]")
    if is_collection:
        stripped = stripped[5:-1].strip()
    if stripped.startswith("dict["):
        return "dict", False
    return stripped, is_collection


def detail_sections(spec: Spec) -> list[dict[str, Any]]:
    sections = []
    for key in ("open_questions",):
        value = spec.data.get(key)
        if isinstance(value, list) and value:
            sections.append(
                {
                    "title": field_label(key),
                    "items": [display_value(item) for item in value],
                }
            )
    return sections


def concept_sections(
    *node_groups: list[dict[str, Any]], include_related: bool = True
) -> list[dict[str, Any]]:
    sections = [
        {"role": "invariant", "title": "Invariants", "items": []},
        {"role": "lifecycle_value", "title": "Status Values", "items": []},
        {"role": None, "title": "Related Concepts", "items": []},
    ]
    by_role = {section["role"]: section for section in sections}
    seen: set[str] = set()
    for nodes in node_groups:
        for node in nodes:
            if node.get("type") not in {"concept", "lifecycle_value"}:
                continue
            node_id = str(node.get("id", ""))
            if node_id in seen:
                continue
            seen.add(node_id)
            role = (
                "lifecycle_value"
                if node.get("type") == "lifecycle_value"
                else node.get("concept_role")
            )
            if role is None and not include_related:
                continue
            section = by_role.get(role, by_role[None])
            section["items"].append(node)
    return [section for section in sections if section["items"]]


def visible_link_nodes(spec: Spec, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if spec.kind == "decision":
        return nodes
    return [node for node in nodes if node.get("type") != "decision"]


def primary_statement(spec: Spec) -> str:
    for key in (
        "decision",
        "statement",
        "purpose",
        "gap",
        "suggested_improvement",
        "summary",
        "definition",
        "command",
        "test",
        "intro",
    ):
        value = spec.data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return spec.description


def field_value(spec: Spec, key: str, default: str = "") -> str:
    value = spec.data.get(key, default)
    if value is None:
        return default
    return display_value(value)


def list_values(spec: Spec, key: str) -> list[str]:
    value = spec.data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    return [str(item) for item in value if isinstance(item, str) and item]


def specs_for_refs(spec: Spec, registry: SpecRegistry, key: str) -> list[Spec]:
    return specs_for_ids(list_values(spec, key), registry)


def specs_for_ids(ids: list[str], registry: SpecRegistry) -> list[Spec]:
    specs: list[Spec] = []
    for spec_id in ids:
        target = registry.by_id.get(spec_id)
        if target is not None:
            specs.append(target)
    return specs


def specs_of_kind(registry: SpecRegistry, kind: str) -> list[Spec]:
    return sorted(
        [spec for spec in registry.active_specs if spec.kind == kind],
        key=lambda spec: spec.id,
    )


def specs_referencing(
    registry: SpecRegistry, target_id: str, *, field: str | None = None
) -> list[Spec]:
    matches: list[Spec] = []
    for spec in registry.active_specs:
        fields = [field] if field is not None else spec.data.keys()
        for key in fields:
            value = spec.data.get(key)
            if value == target_id:
                matches.append(spec)
                break
            if isinstance(value, list) and target_id in value:
                matches.append(spec)
                break
    return sorted(matches, key=lambda spec: (spec.kind, spec.id))


def grouped_related_nodes(
    spec: Spec,
    outgoing: list[dict[str, Any]],
    backlinks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups = [
        {"title": "Outgoing References", "items": visible_link_nodes(spec, outgoing)},
        {"title": "Referenced By", "items": visible_link_nodes(spec, backlinks)},
    ]
    return [group for group in groups if group["items"]]


def document_artifacts(registry: SpecRegistry) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for spec in specs_of_kind(registry, "generated_document"):
        output_path = field_value(spec, "output_path")
        artifacts.append(
            {
                "spec": spec,
                "path": output_path,
                "format": field_value(spec, "format", "markdown"),
                "write_mode": field_value(spec, "write_mode", "protected_block"),
                "section_count": len(list_values(spec, "section_refs")),
            }
        )
    return sorted(artifacts, key=lambda item: item["path"])


def documentation_sets(registry: SpecRegistry) -> list[Spec]:
    return specs_of_kind(registry, "documentation_set")


def generated_documents(registry: SpecRegistry) -> list[Spec]:
    return specs_of_kind(registry, "generated_document")


def primary_story_specs(registry: SpecRegistry) -> list[Spec]:
    preferred = [
        *specs_of_kind(registry, "generated_document"),
        *specs_of_kind(registry, "decision"),
        *specs_of_kind(registry, "guardrail"),
        *specs_of_kind(registry, "workflow"),
    ]
    return preferred[:12]


def value_type_name(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "string"


def display_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value).lower()
    return json.dumps(value, sort_keys=True)
