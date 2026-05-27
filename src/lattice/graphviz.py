from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Literal

from .models import Spec
from .registry import SpecRegistry
from .render_display import display_name
from .render_graph import graph_reference_ids_for

GraphProfile = Literal["debug", "docs", "compact"]


@dataclass(frozen=True)
class DotNode:
    id: str
    title: str
    kind: str
    spec_id: str
    fill: str = "#fffefb"
    border: str = "#d8cfc5"
    accent: bool = False
    detail: str | None = None


@dataclass(frozen=True)
class DotEdge:
    source: str
    target: str
    label: str | None = None


def graphviz_dot_for(
    registry: SpecRegistry,
    start_id: str,
    *,
    depth: int = 1,
    include_types: set[str] | None = None,
    exclude_types: set[str] | None = None,
    profile: GraphProfile = "docs",
) -> str:
    if depth < 0:
        raise ValueError("depth must be greater than or equal to 0")
    if profile not in {"debug", "docs", "compact"}:
        raise ValueError("profile must be one of: debug, docs, compact")
    if start_id not in registry.by_id:
        raise KeyError(start_id)
    if not _type_is_included(registry.by_id[start_id], include_types, exclude_types):
        raise ValueError(
            f"starting knowledge-unit type {registry.by_id[start_id].kind} is excluded by type filters"
        )

    active_ids = {
        spec.id
        for spec in registry.active_specs
        if _type_is_included(spec, include_types, exclude_types)
    }
    outgoing = _outgoing_edges(registry, active_ids)
    incoming = _incoming_edges(outgoing)
    included = _related_ids(start_id, depth, outgoing, incoming)
    nodes = sorted(
        (registry.by_id[spec_id] for spec_id in included),
        key=lambda spec: (spec.kind, spec.id),
    )
    edges = sorted(
        (source, target)
        for source in included
        for target in outgoing.get(source, ())
        if target in included
    )
    if profile == "debug":
        return _debug_dot(nodes, edges)
    return _presentation_dot(
        registry,
        start_id,
        nodes,
        edges,
        outgoing,
        profile=profile,
        show_edge_labels=depth <= 2,
    )


def _debug_dot(nodes: list[Spec], edges: list[tuple[str, str]]) -> str:
    lines = [
        "digraph lattice {",
        '  graph [rankdir="LR"];',
        '  node [shape="box", style="rounded", fontname="Helvetica"];',
        '  edge [fontname="Helvetica"];',
    ]
    for spec in nodes:
        lines.append(f'  "{_dot_escape(spec.id)}" [label="{_node_label(spec)}"];')
    for source, target in edges:
        lines.append(f'  "{_dot_escape(source)}" -> "{_dot_escape(target)}";')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _presentation_dot(
    registry: SpecRegistry,
    start_id: str,
    nodes: list[Spec],
    edges: list[tuple[str, str]],
    outgoing: dict[str, tuple[str, ...]],
    *,
    profile: GraphProfile,
    show_edge_labels: bool,
) -> str:
    visible_ids = {spec.id for spec in nodes}
    lifecycle_values = _collapsed_lifecycle_values(registry, visible_ids, outgoing)
    collapsed_value_ids = {
        value_id for value_ids in lifecycle_values.values() for value_id in value_ids
    }
    hide_kinds = {"data_type", "spec_type"}
    if profile == "compact":
        hide_kinds.update({"schema_gap", "test_binding", "verification"})

    dot_nodes: dict[str, DotNode] = {}
    for spec in nodes:
        if spec.id in collapsed_value_ids or spec.kind in hide_kinds:
            continue
        dot_nodes[spec.id] = _dot_node_for_spec(spec, accent=spec.id == start_id)

    dot_edges: list[DotEdge] = []
    for source, target in edges:
        if source in collapsed_value_ids or target in collapsed_value_ids:
            continue
        if source not in dot_nodes or target not in dot_nodes:
            continue
        dot_edges.append(
            DotEdge(
                source=source,
                target=target,
                label=_edge_label(registry, start_id, source, target)
                if show_edge_labels
                else None,
            )
        )

    for lifecycle_id, value_ids in lifecycle_values.items():
        if lifecycle_id not in dot_nodes:
            continue
        values = [
            display_name(registry.by_id[value_id])
            for value_id in value_ids
            if value_id in registry.by_id
        ]
        if not values:
            continue
        summary_id = f"{lifecycle_id}::values"
        dot_nodes[summary_id] = DotNode(
            id=summary_id,
            title=f"{display_name(registry.by_id[lifecycle_id])} values",
            kind="status values",
            spec_id="collapsed",
            fill="#f8f4f0",
            border="#d8cfc5",
            detail=" | ".join(values),
        )
        dot_edges.append(
            DotEdge(
                source=lifecycle_id,
                target=summary_id,
                label="has values" if show_edge_labels else None,
            )
        )

    start = registry.by_id[start_id]
    field_summary = _field_summary(start)
    if field_summary and start_id in dot_nodes:
        fields_id = f"{start_id}::fields"
        dot_nodes[fields_id] = DotNode(
            id=fields_id,
            title=f"{display_name(start)} fields",
            kind="fields",
            spec_id="collapsed",
            fill="#f8f4f0",
            border="#d8cfc5",
            detail=field_summary,
        )
        dot_edges.append(
            DotEdge(
                source=start_id,
                target=fields_id,
                label="has fields" if show_edge_labels else None,
            )
        )

    lines = [
        "digraph lattice {",
        "  graph [",
        '    rankdir="LR",',
        '    bgcolor="#fffefb",',
        '    pad="0.4",',
        '    nodesep="0.45",',
        '    ranksep="0.8",',
        "    splines=true,",
        "    overlap=false,",
        "    concentrate=true,",
        "    outputorder=edgesfirst",
        "  ];",
        '  node [shape=plain, fontname="Inter", fontsize=12, margin=0];',
        '  edge [color="#7a7168", arrowsize=0.7, penwidth=1.1, fontname="Inter", fontsize=10, fontcolor="#605d52"];',
    ]
    sorted_nodes = sorted(dot_nodes.values(), key=lambda item: (item.kind, item.id))
    if profile == "docs":
        lines.extend(_clustered_node_lines(sorted_nodes))
    else:
        for node in sorted_nodes:
            lines.append(f'  "{_dot_escape(node.id)}" [label=<{_html_label(node)}>];')
    for edge in sorted(dot_edges, key=lambda item: (item.source, item.target)):
        attrs = ""
        if edge.label:
            attrs = f' [label="{_dot_escape(edge.label)}"]'
        lines.append(
            f'  "{_dot_escape(edge.source)}" -> "{_dot_escape(edge.target)}"{attrs};'
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _type_is_included(
    spec: Spec, include_types: set[str] | None, exclude_types: set[str] | None
) -> bool:
    if include_types and spec.kind not in include_types:
        return False
    return not (exclude_types and spec.kind in exclude_types)


def _outgoing_edges(
    registry: SpecRegistry, active_ids: set[str]
) -> dict[str, tuple[str, ...]]:
    return {
        spec.id: tuple(
            target_id
            for target_id in graph_reference_ids_for(spec)
            if target_id in active_ids
        )
        for spec in registry.active_specs
        if spec.id in active_ids
    }


def _incoming_edges(outgoing: dict[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
    incoming: dict[str, list[str]] = {}
    for source, targets in outgoing.items():
        for target in targets:
            incoming.setdefault(target, []).append(source)
    return {target: tuple(sorted(sources)) for target, sources in incoming.items()}


def _related_ids(
    start_id: str,
    depth: int,
    outgoing: dict[str, tuple[str, ...]],
    incoming: dict[str, tuple[str, ...]],
) -> set[str]:
    included = {start_id}
    frontier = {start_id}
    for _ in range(depth):
        next_frontier: set[str] = set()
        for spec_id in frontier:
            next_frontier.update(outgoing.get(spec_id, ()))
            next_frontier.update(incoming.get(spec_id, ()))
        next_frontier.difference_update(included)
        if not next_frontier:
            break
        included.update(next_frontier)
        frontier = next_frontier
    return included


def _node_label(spec: Spec) -> str:
    return _dot_escape(f"{display_name(spec)}\\n{spec.kind}\\n{spec.id}")


def _dot_node_for_spec(spec: Spec, *, accent: bool = False) -> DotNode:
    border, fill = _style_for_kind(spec.kind)
    return DotNode(
        id=spec.id,
        title=display_name(spec),
        kind=_human_kind(spec.kind),
        spec_id=spec.id,
        fill=fill,
        border="#ff6a00" if accent else border,
        accent=accent,
    )


def _style_for_kind(kind: str) -> tuple[str, str]:
    if kind == "business_entity":
        return "#d8cfc5", "#fffefb"
    if kind in {"concept", "workflow"}:
        return "#d8cfc5", "#fbf7f0"
    if kind in {"data_type", "lifecycle_value"}:
        return "#d8cfc5", "#f8f4f0"
    if kind == "lifecycle_type":
        return "#c8beb3", "#fffefb"
    return "#d8cfc5", "#fffefb"


def _human_kind(kind: str) -> str:
    return kind.replace("_", " ")


def _html_label(node: DotNode) -> str:
    border_width = "2" if node.accent else "1"
    rows = [
        "<TR><TD>"
        f'<FONT POINT-SIZE="16"><B>{escape(node.title)}</B></FONT>'
        "</TD></TR>",
        "<TR><TD>"
        f'<FONT FACE="monospace" POINT-SIZE="10">{escape(node.spec_id)}</FONT>'
        "</TD></TR>",
        "<TR><TD>"
        f'<FONT POINT-SIZE="10" COLOR="#605d52">{escape(node.kind)}</FONT>'
        "</TD></TR>",
    ]
    if node.detail:
        rows.append(
            "<TR><TD>"
            f'<FONT POINT-SIZE="10" COLOR="#37352f">{escape(node.detail)}</FONT>'
            "</TD></TR>"
        )
    return (
        f'<TABLE BORDER="{border_width}" CELLBORDER="0" CELLSPACING="0" '
        f'CELLPADDING="8" COLOR="{node.border}" BGCOLOR="{node.fill}">'
        f'{"".join(rows)}</TABLE>'
    )


def _clustered_node_lines(nodes: list[DotNode]) -> list[str]:
    groups: dict[str, list[DotNode]] = {}
    for node in nodes:
        groups.setdefault(node.kind, []).append(node)

    lines: list[str] = []
    for kind, group in sorted(groups.items()):
        cluster_id = _cluster_id(kind)
        lines.extend(
            [
                f"  subgraph {cluster_id} {{",
                f'    label="{_dot_escape(kind.title())}";',
                '    color="#ede9e4";',
                '    style="rounded";',
                '    fontname="Inter";',
                '    fontsize=11;',
                '    fontcolor="#605d52";',
            ]
        )
        for node in group:
            lines.append(
                f'    "{_dot_escape(node.id)}" [label=<{_html_label(node)}>];'
            )
        lines.append("  }")
    return lines


def _cluster_id(kind: str) -> str:
    safe = "".join(character if character.isalnum() else "_" for character in kind)
    return f"cluster_{safe}"


def _collapsed_lifecycle_values(
    registry: SpecRegistry,
    visible_ids: set[str],
    outgoing: dict[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    collapsed: dict[str, tuple[str, ...]] = {}
    for spec_id in visible_ids:
        spec = registry.by_id.get(spec_id)
        if spec is None or spec.kind != "lifecycle_type":
            continue
        values = tuple(
            target_id
            for target_id in outgoing.get(spec_id, ())
            if target_id in visible_ids
            and registry.by_id.get(target_id) is not None
            and registry.by_id[target_id].kind == "lifecycle_value"
        )
        if values:
            collapsed[spec_id] = values
    return collapsed


def _field_summary(spec: Spec) -> str | None:
    fields = spec.data.get("fields")
    if not isinstance(fields, list):
        return None
    labels: list[str] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get("name")
        field_type = field.get("type")
        if isinstance(name, str) and name and isinstance(field_type, str) and field_type:
            labels.append(f"{name}: {field_type}")
    return " | ".join(labels) if labels else None


def _edge_label(
    registry: SpecRegistry, start_id: str, source: str, target: str
) -> str:
    source_spec = registry.by_id[source]
    target_spec = registry.by_id[target]
    if target_spec.kind == "lifecycle_type":
        return "has status"
    if source == start_id and target_spec.kind == "business_entity":
        return "depends on"
    if target == start_id:
        return "mentions"
    if source_spec.kind == "workflow":
        return "uses"
    return "references"


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
