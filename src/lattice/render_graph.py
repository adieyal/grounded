from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import LatticeConfig, Spec
from .registry import SpecRegistry
from .render_display import display_fields, display_name
from .render_paths import href_for, unit_output_path


def lattice_key(spec: Spec) -> str:
    return f"{spec.kind}:{spec.id}"


def graph_reference_ids_for(spec: Spec) -> tuple[str, ...]:
    return tuple(dict.fromkeys(spec.references))


def lattice_registry_for(
    config: LatticeConfig,
    registry: SpecRegistry,
    from_path: Path,
    *,
    specs: list[Spec] | None = None,
) -> dict[str, dict[str, Any]]:
    outgoing: dict[str, list[str]] = {}
    backlinks: dict[str, list[str]] = {}
    graph_specs = specs if specs is not None else registry.active_specs
    graph_ids = {spec.id for spec in graph_specs}

    for spec in graph_specs:
        source = lattice_key(spec)
        targets = [
            target
            for target in graph_reference_ids_for(spec)
            if target in registry.by_id and target in graph_ids
        ]
        outgoing[source] = [lattice_key(registry.by_id[target]) for target in targets]
        for target in targets:
            backlinks.setdefault(lattice_key(registry.by_id[target]), []).append(source)

    graph: dict[str, dict[str, Any]] = {}
    for spec in graph_specs:
        key = lattice_key(spec)
        graph[key] = {
            "type": spec.kind,
            "id": spec.id,
            "label": display_name(spec),
            "href": href_for(from_path, unit_output_path(config, spec)),
            "summary": spec.description,
            "concept_role": spec.data.get("concept_role"),
            "outgoing": outgoing.get(key, []),
            "backlinks": [
                {
                    "type": registry.by_id[source_id].kind,
                    "id": registry.by_id[source_id].id,
                    "label": display_name(registry.by_id[source_id]),
                    "summary": registry.by_id[source_id].description,
                    "concept_role": registry.by_id[source_id].data.get("concept_role"),
                    "href": href_for(
                        from_path, unit_output_path(config, registry.by_id[source_id])
                    ),
                }
                for source_key in sorted(backlinks.get(key, []))
                for source_id in [source_key.split(":", 1)[1]]
                if source_id in registry.by_id
            ],
        }
    return graph


def outgoing_links_for(
    spec: Spec, registry: SpecRegistry, graph: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    links = []
    for target_id in graph_reference_ids_for(spec):
        target = registry.by_id.get(target_id)
        if target is None:
            continue
        node = graph.get(lattice_key(target))
        if node is not None:
            links.append(node)
    return links


def build_search_index(
    config: LatticeConfig,
    registry: SpecRegistry,
    graph: dict[str, dict[str, Any]],
    *,
    specs: list[Spec] | None = None,
) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []
    for spec in sorted(
        specs if specs is not None else registry.active_specs,
        key=lambda item: (item.kind, item.id),
    ):
        type_def = registry.type_definition_for(spec)
        fields = type_def.search_fields if type_def else ("id", "name", "summary")
        text_parts = [
            str(spec.id),
            str(spec.kind),
            str(spec.data.get("name", "")),
            str(spec.short_name or ""),
        ]
        text_parts.extend(spec.tags)
        for field in display_fields(spec):
            text_parts.extend(field.get("tags", []))
        for field in fields:
            text_parts.extend(flatten_search_value(spec.data.get(field)))
        node = graph[lattice_key(spec)]
        text_parts.extend(
            str(backlink["label"]) for backlink in node.get("backlinks", [])
        )
        index.append(
            {
                "id": spec.id,
                "type": spec.kind,
                "name": display_name(spec),
                "summary": spec.description,
                "href": node["href"],
                "text": " ".join(part for part in text_parts if part).lower(),
                "backlinks": len(node.get("backlinks", [])),
            }
        )
    return index


def flatten_search_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(flatten_search_value(item))
        return result
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(flatten_search_value(item))
        return result
    return [str(value)]
