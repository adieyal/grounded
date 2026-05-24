from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import LatticeConfig, Spec
from .registry import SpecRegistry
from .render_display import (
    display_fields,
    display_name,
    display_value,
    field_anchor,
    type_nav_label,
)
from .render_paths import href_for, slugify, unit_output_path


def tag_values(spec: Spec) -> tuple[str, ...]:
    return spec.tags


def tag_output_path(config: LatticeConfig, tag: str) -> Path:
    return config.generated_docs_dir / "tags" / f"{slugify(tag)}.html"


def tag_index_for(
    config: LatticeConfig, registry: SpecRegistry, from_path: Path
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for tag, entries in tags_by_name(registry.active_specs, config, from_path).items():
        index[tag] = {
            "href": href_for(from_path, tag_output_path(config, tag)),
            "label": tag,
            "count": len(entries),
        }
    return index


def tags_by_name(
    specs: list[Spec], config: LatticeConfig, from_path: Path
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for spec in specs:
        for tag in spec.tags:
            grouped[tag].append(
                {
                    "type": spec.kind,
                    "id": spec.id,
                    "label": display_name(spec),
                    "summary": spec.statement,
                    "href": href_for(from_path, unit_output_path(config, spec)),
                }
            )
        for field in display_fields(spec):
            for tag in field.get("tags", []):
                grouped[tag].append(
                    {
                        "type": spec.kind,
                        "id": spec.id,
                        "label": f"{display_name(spec)}.{field['name']}",
                        "summary": display_value(field.get("description") or field["name"]),
                        "href": href_for(from_path, unit_output_path(config, spec)),
                        "fragment": field_anchor(spec.id, field["name"]),
                        "field_name": field["name"],
                    }
                )
    return {
        tag: sorted(
            values,
            key=lambda item: (
                item["type"],
                item["id"],
                item.get("field_name", ""),
                item["label"],
            ),
        )
        for tag, values in sorted(grouped.items())
    }


def tag_sections_for(
    tag: str, specs: list[Spec], config: LatticeConfig, from_path: Path
) -> list[dict[str, Any]]:
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in specs:
        by_type[entry["type"]].append(entry)

    return [
        {"title": type_nav_label(type_name), "items": items}
        for type_name, items in sorted(by_type.items())
    ]
