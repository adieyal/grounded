from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import GroundedConfig, Spec
from .registry import SpecRegistry
from .render_display import display_fields, display_name
from .render_paths import href_for, unit_output_path


def grounded_key(spec: Spec) -> str:
    return f"{spec.kind}:{spec.id}"


def graph_reference_ids_for(spec: Spec) -> tuple[str, ...]:
    return tuple(dict.fromkeys(spec.references))


def grounded_registry_for(
    config: GroundedConfig,
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
        source = grounded_key(spec)
        targets = [
            edge.target_id
            for edge in registry.outgoing_edges_for(spec.id)
            if edge.target_id in registry.by_id and edge.target_id in graph_ids
        ]
        outgoing[source] = [grounded_key(registry.by_id[target]) for target in targets]
        for target in targets:
            backlinks.setdefault(grounded_key(registry.by_id[target]), []).append(
                source
            )

    graph: dict[str, dict[str, Any]] = {}
    for spec in graph_specs:
        key = grounded_key(spec)
        graph[key] = {
            "type": spec.kind,
            "id": spec.id,
            "label": display_name(spec),
            "href": href_for(from_path, unit_output_path(config, spec)),
            "summary": spec.description,
            "concept_role": spec.data.get("concept_role"),
            "outgoing": outgoing.get(key, []),
            "outgoing_edges": [
                _edge_node_payload(edge, config, registry, from_path)
                for edge in registry.outgoing_edges_for(spec.id)
                if edge.target_id in graph_ids and edge.target_id in registry.by_id
            ],
            "backlinks": [
                _edge_node_payload(edge, config, registry, from_path, incoming=True)
                for edge in registry.incoming_edges_for(spec.id)
                if edge.source_id in graph_ids and edge.source_id in registry.by_id
            ],
        }
    return graph


def outgoing_links_for(
    spec: Spec, registry: SpecRegistry, graph: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    links = []
    for edge in registry.outgoing_edges_for(spec.id):
        target = registry.by_id.get(edge.target_id)
        if target is None:
            continue
        node = graph.get(grounded_key(target))
        if node is not None:
            links.append({**node, "edge_type": edge.edge_type})
    return links


def _edge_node_payload(
    edge: object,
    config: GroundedConfig,
    registry: SpecRegistry,
    from_path: Path,
    *,
    incoming: bool = False,
) -> dict[str, Any]:
    source_id = getattr(edge, "source_id")
    target_id = getattr(edge, "target_id")
    spec_id = source_id if incoming else target_id
    spec = registry.by_id[spec_id]
    return {
        "type": spec.kind,
        "id": spec.id,
        "label": display_name(spec),
        "summary": spec.description,
        "concept_role": spec.data.get("concept_role"),
        "href": href_for(from_path, unit_output_path(config, spec)),
        "edge_type": getattr(edge, "edge_type"),
        "source_field": getattr(edge, "source_field"),
        "authored": getattr(edge, "authored"),
    }


def build_search_index(
    config: GroundedConfig,
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
        node = graph[grounded_key(spec)]
        text_parts.extend(
            str(backlink["label"]) for backlink in node.get("backlinks", [])
        )
        text_parts.extend(
            f"{edge.get('edge_type')} {edge.get('label')}"
            for edge in node.get("outgoing_edges", [])
            if isinstance(edge, dict)
        )
        text_parts.extend(
            f"{edge.get('edge_type')} {edge.get('label')}"
            for edge in node.get("backlinks", [])
            if isinstance(edge, dict)
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
