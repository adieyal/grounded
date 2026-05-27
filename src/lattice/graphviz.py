from __future__ import annotations

from .models import Spec
from .registry import SpecRegistry
from .render_display import display_name
from .render_graph import graph_reference_ids_for


def graphviz_dot_for(
    registry: SpecRegistry,
    start_id: str,
    *,
    depth: int = 1,
    include_types: set[str] | None = None,
    exclude_types: set[str] | None = None,
) -> str:
    if depth < 0:
        raise ValueError("depth must be greater than or equal to 0")
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


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
