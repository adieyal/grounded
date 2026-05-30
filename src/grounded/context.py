from __future__ import annotations

from collections import deque
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .models import Spec
from .registry import SpecRegistry
from .rich_text import rich_text_plain
from .search import SearchResult, build_search_records, search_records


@dataclass(frozen=True)
class ContextItem:
    spec: Spec
    distance: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ContextPack:
    start: str
    seed: Spec
    seed_reason: str
    seed_resolution: Literal["exact_id", "search"]
    alternatives: tuple[SearchResult, ...]
    items: tuple[ContextItem, ...]


def build_context_pack(
    registry: SpecRegistry,
    start: str,
    *,
    depth: int = 1,
    limit: int = 12,
) -> ContextPack | None:
    if depth < 0:
        raise ValueError("depth must be >= 0")
    if limit < 1:
        raise ValueError("limit must be >= 1")

    seed, seed_reason, seed_resolution, alternatives = _resolve_seed(registry, start)
    if seed is None:
        return None

    active_ids = {spec.id for spec in registry.active_specs}
    distances: dict[str, int] = {seed.id: 0}
    reasons: dict[str, list[str]] = {seed.id: [seed_reason]}
    queue: deque[Spec] = deque([seed])

    while queue:
        current = queue.popleft()
        current_distance = distances[current.id]
        if current_distance >= depth:
            continue
        for neighbor_id, reason in _neighbors(registry, current.id):
            if neighbor_id not in active_ids:
                continue
            existing = distances.get(neighbor_id)
            next_distance = current_distance + 1
            if existing is None:
                distances[neighbor_id] = next_distance
                reasons.setdefault(neighbor_id, []).append(reason)
                neighbor = registry.get(neighbor_id)
                if neighbor is not None:
                    queue.append(neighbor)
            elif existing == next_distance:
                reasons.setdefault(neighbor_id, []).append(reason)

    ordered_ids = sorted(
        distances,
        key=lambda spec_id: (
            distances[spec_id],
            0 if spec_id == seed.id else 1,
            registry.by_id[spec_id].kind,
            spec_id,
        ),
    )[:limit]
    items = tuple(
        ContextItem(
            spec=registry.by_id[spec_id],
            distance=distances[spec_id],
            reasons=tuple(dict.fromkeys(reasons.get(spec_id, ()))),
        )
        for spec_id in ordered_ids
    )
    return ContextPack(
        start=start,
        seed=seed,
        seed_reason=seed_reason,
        seed_resolution=seed_resolution,
        alternatives=alternatives,
        items=items,
    )


def render_context_pack_markdown(
    pack: ContextPack, registry: SpecRegistry, *, root: Path | None = None
) -> str:
    included_ids = {item.spec.id for item in pack.items}
    lines = [
        "# Grounded Focused Context",
        "",
        f"Start: `{pack.start}`",
        f"Seed: `{pack.seed.id}` ({pack.seed.kind}) - {pack.seed.display_name}",
        f"Seed reason: {pack.seed_reason}",
        "",
    ]
    if pack.seed_resolution == "exact_id":
        lines.extend(
            [
                "Use these canonical specs as the focused source of truth. Do not duplicate or invent competing facts.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "Warning: START was resolved by search, not exact ID. Verify the seed before treating this pack as authoritative.",
                "",
            ]
        )
    if pack.alternatives:
        lines.extend(["## Other Matches", ""])
        for result in pack.alternatives:
            lines.append(
                f"- `{result.record.id}` ({result.record.kind}, {result.score}): "
                f"{result.record.name} - {result.reason}"
            )
        lines.append("")

    lines.extend(["## Context Specs", ""])
    for item in pack.items:
        spec = item.spec
        summary = rich_text_plain(spec.description, registry)
        if spec.statement and spec.statement != spec.description:
            summary = f"{summary} {rich_text_plain(spec.statement, registry)}"
        lines.append(f"### `{spec.id}` - {spec.display_name}")
        lines.append("")
        lines.append(f"- Type: `{spec.kind}`")
        lines.append(f"- Owner: `{spec.owner or 'unknown'}`")
        lines.append(f"- Distance: `{item.distance}`")
        lines.append(f"- Path: `{_display_path(spec, root)}`")
        if item.reasons:
            lines.append(f"- Included because: {'; '.join(item.reasons)}")
        if summary:
            lines.append(f"- Summary: {summary}")
        refs = ", ".join(f"`{ref}`" for ref in spec.references)
        if refs:
            lines.append(f"- Links: {refs}")
        edge_lines = _typed_edge_lines(spec, registry, included_ids)
        if edge_lines:
            lines.extend(f"- {line}" for line in edge_lines)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def context_pack_json(
    pack: ContextPack, registry: SpecRegistry, *, root: Path | None = None
) -> str:
    included_ids = {item.spec.id for item in pack.items}
    return json.dumps(
        {
            "start": pack.start,
            "seed": _spec_payload(pack.seed, registry, included_ids, root),
            "seed_reason": pack.seed_reason,
            "seed_resolution": pack.seed_resolution,
            "alternatives": [
                {
                    "score": result.score,
                    "reason": result.reason,
                    "id": result.record.id,
                    "kind": result.record.kind,
                    "name": result.record.name,
                    "path": _display_path_for_path(Path(result.record.path), root),
                }
                for result in pack.alternatives
            ],
            "items": [
                {
                    "distance": item.distance,
                    "reasons": list(item.reasons),
                    **_spec_payload(item.spec, registry, included_ids, root),
                }
                for item in pack.items
            ],
        },
        indent=2,
    )


def _resolve_seed(
    registry: SpecRegistry, start: str
) -> tuple[Spec | None, str, Literal["exact_id", "search"], tuple[SearchResult, ...]]:
    active_ids = {spec.id for spec in registry.active_specs}
    exact = registry.get(start)
    if exact is not None and exact.id in active_ids:
        return exact, "exact id match", "exact_id", ()

    records = [
        record for record in build_search_records(registry) if record.id in active_ids
    ]
    results = search_records(records, start, kind="all", limit=4)
    if not results:
        return None, "", "search", ()

    seed = registry.get(results[0].record.id)
    if seed is None:
        return None, "", "search", ()
    return seed, results[0].reason, "search", tuple(results[1:])


def _neighbors(registry: SpecRegistry, spec_id: str) -> list[tuple[str, str]]:
    neighbors: list[tuple[str, str]] = []
    for edge in registry.outgoing_edges_for(spec_id):
        neighbors.append(
            (
                edge.target_id,
                f"{spec_id} {edge.edge_type} -> {edge.target_id}",
            )
        )
    for edge in registry.incoming_edges_for(spec_id):
        neighbors.append(
            (
                edge.source_id,
                f"{edge.source_id} {edge.edge_type} -> {spec_id}",
            )
        )
    return sorted(dict.fromkeys(neighbors), key=lambda item: item[0])


def _typed_edge_lines(
    spec: Spec, registry: SpecRegistry, included_ids: set[str]
) -> list[str]:
    outgoing = [
        f"{edge.edge_type} -> `{edge.target_id}`"
        for edge in registry.outgoing_edges_for(spec.id)
        if edge.target_id in included_ids
    ]
    incoming = [
        f"{edge.edge_type} <- `{edge.source_id}`"
        for edge in registry.incoming_edges_for(spec.id)
        if edge.source_id in included_ids
    ]
    lines: list[str] = []
    if outgoing:
        lines.append(f"Edges: {', '.join(outgoing)}")
    if incoming:
        lines.append(f"Incoming edges: {', '.join(incoming)}")
    return lines


def _spec_payload(
    spec: Spec, registry: SpecRegistry, included_ids: set[str], root: Path | None
) -> dict[str, Any]:
    return {
        "id": spec.id,
        "kind": spec.kind,
        "name": spec.display_name,
        "owner": spec.owner,
        "status": spec.status,
        "path": _display_path(spec, root),
        "description": rich_text_plain(spec.description, registry),
        "references": list(spec.references),
        "outgoing_edges": [
            {
                "type": edge.edge_type,
                "target": edge.target_id,
                "source_field": edge.source_field,
            }
            for edge in registry.outgoing_edges_for(spec.id)
            if edge.target_id in included_ids
        ],
        "incoming_edges": [
            {
                "type": edge.edge_type,
                "source": edge.source_id,
                "source_field": edge.source_field,
            }
            for edge in registry.incoming_edges_for(spec.id)
            if edge.source_id in included_ids
        ],
    }


def _display_path(spec: Spec, root: Path | None) -> str:
    return _display_path_for_path(spec.path, root)


def _display_path_for_path(path: Path, root: Path | None) -> str:
    if root is not None:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return path.as_posix()
