from __future__ import annotations

import json
from html import escape
from typing import Any

from .models import Spec
from .registry import SpecRegistry
from .render_paths import slugify
from .tags import tag_keys


def lattice_link(
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
        f'<lattice-link type="{escape(str(type_name))}" lattice-id="{escape(str(unit_id))}"{label_attr}{fragment_attr}{variant_attr}>'
        f"{escape(text)}</lattice-link>"
    )


def field_label(value: str) -> str:
    return value.replace("_", " ").title()


TYPE_TONES = {
    "business_entity": "ent",
    "domain_object": "ent",
    "concept": "con",
    "enum": "enu",
    "lifecycle_type": "enu",
    "lifecycle_value": "enu",
    "data_type": "type",
    "workflow": "flow",
    "registry_type": "type",
    "spec_type": "type",
}


TYPE_NAV_LABELS = {
    "business_entity": "Business Entities",
    "domain_object": "Domain",
    "concept": "Concepts",
    "enum": "Enums",
    "lifecycle_type": "Lifecycle Types",
    "lifecycle_value": "Lifecycle Values",
    "data_type": "Data Types",
    "workflow": "Workflows",
    "registry_type": "Lattice Types",
    "spec_type": "Lattice Types",
}


def type_tone(type_name: object) -> str:
    return TYPE_TONES.get(str(type_name), "meta")


def type_nav_label(type_name: object) -> str:
    return TYPE_NAV_LABELS.get(str(type_name), field_label(str(type_name)))


def page_component(type_name: object) -> str:
    components = {
        "business_entity": "lattice-business-entity-page",
        "domain_object": "lattice-domain-object-page",
        "enum": "lattice-enum-page",
        "lifecycle_type": "lattice-lifecycle-type-page",
    }
    return components.get(str(type_name), "lattice-unit-page")


DETAIL_FIELD_EXCLUDES = {
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

    rendered = lattice_link(target.kind, target.id, display_name(target), "field-type")
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
