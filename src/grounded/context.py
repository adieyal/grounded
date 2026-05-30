from __future__ import annotations

from collections import deque
import json
import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .bindings import Binding, BindingOmissionReason, bindings_for_spec
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
    seed_resolution: Literal["exact_id", "search", "changed_files"]
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

    return _build_context_pack_from_seeds(
        registry,
        start=start,
        seeds=((seed, seed_reason),),
        seed_resolution=seed_resolution,
        alternatives=alternatives,
        depth=depth,
        limit=limit,
    )


def build_context_pack_for_changed_files(
    registry: SpecRegistry,
    changed_files: tuple[str, ...],
    *,
    root: Path | None = None,
    depth: int = 1,
    limit: int = 12,
) -> ContextPack | None:
    if depth < 0:
        raise ValueError("depth must be >= 0")
    if limit < 1:
        raise ValueError("limit must be >= 1")

    normalized_files = tuple(
        dict.fromkeys(
            _normalize_changed_file_path(changed_file, root)
            for changed_file in changed_files
        )
    )
    seeds = _seeds_for_changed_files(registry, normalized_files, root=root)
    if not seeds:
        return None

    return _build_context_pack_from_seeds(
        registry,
        start=", ".join(normalized_files),
        seeds=seeds,
        seed_resolution="changed_files",
        alternatives=(),
        depth=depth,
        limit=limit,
    )


def _build_context_pack_from_seeds(
    registry: SpecRegistry,
    *,
    start: str,
    seeds: tuple[tuple[Spec, str], ...],
    seed_resolution: Literal["exact_id", "search", "changed_files"],
    alternatives: tuple[SearchResult, ...],
    depth: int,
    limit: int,
) -> ContextPack:
    active_ids = {spec.id for spec in registry.active_specs}
    seed_order = {spec.id: index for index, (spec, _) in enumerate(seeds)}
    distances: dict[str, int] = {}
    reasons: dict[str, list[str]] = {}
    queue: deque[Spec] = deque()

    for seed, reason in seeds:
        if seed.id not in active_ids:
            continue
        distances[seed.id] = 0
        reasons.setdefault(seed.id, []).append(reason)
        queue.append(seed)

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
            seed_order.get(spec_id, len(seed_order)),
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
        seed=seeds[0][0],
        seed_reason=seeds[0][1],
        seed_resolution=seed_resolution,
        alternatives=alternatives,
        items=items,
    )


def render_context_pack_markdown(
    pack: ContextPack,
    registry: SpecRegistry,
    *,
    root: Path | None = None,
    include_bindings: bool = False,
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
    elif pack.seed_resolution == "search":
        lines.extend(
            [
                "Warning: START was resolved by search, not exact ID. Verify the seed before treating this pack as authoritative.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "Resolved from declared file bindings. No source-code inference or artifact content is included.",
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
        if include_bindings:
            binding_lines = _binding_lines(
                spec,
                registry,
                root=root,
            )
            if binding_lines:
                lines.append("- Bindings:")
                lines.extend(f"  - {line}" for line in binding_lines)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def context_pack_json(
    pack: ContextPack,
    registry: SpecRegistry,
    *,
    root: Path | None = None,
    include_bindings: bool = False,
) -> str:
    included_ids = {item.spec.id for item in pack.items}
    return json.dumps(
        {
            "start": pack.start,
            "seed": _spec_payload(
                pack.seed,
                registry,
                included_ids,
                root,
                include_bindings=include_bindings,
            ),
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
                    **_spec_payload(
                        item.spec,
                        registry,
                        included_ids,
                        root,
                        include_bindings=include_bindings,
                    ),
                }
                for item in pack.items
            ],
        },
        indent=2,
    )


def _resolve_seed(
    registry: SpecRegistry, start: str
) -> tuple[
    Spec | None,
    str,
    Literal["exact_id", "search", "changed_files"],
    tuple[SearchResult, ...],
]:
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


def _seeds_for_changed_files(
    registry: SpecRegistry,
    changed_files: tuple[str, ...],
    *,
    root: Path | None,
) -> tuple[tuple[Spec, str], ...]:
    seeds: list[tuple[Spec, str]] = []
    seen_ids: set[str] = set()
    specs = sorted(registry.active_specs, key=lambda item: (item.kind, item.id))

    for changed_file in changed_files:
        for spec in specs:
            for binding in _bindings_for_context(spec, registry, root=root):
                if binding.target.kind != "file" or not binding.target.path:
                    continue
                if _binding_omission(binding, include_bindings=True) not in (
                    None,
                    "missing_path",
                ):
                    continue
                target_path = _normalize_changed_file_path(binding.target.path, root)
                if target_path != changed_file:
                    continue
                if spec.id in seen_ids:
                    continue
                seen_ids.add(spec.id)
                seeds.append(
                    (
                        spec,
                        f"declared file binding match: {target_path}",
                    )
                )
    return tuple(seeds)


def _normalize_changed_file_path(changed_file: str, root: Path | None) -> str:
    value = changed_file.strip().replace("\\", "/")
    path = Path(value)
    if root is not None and path.is_absolute():
        try:
            value = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            value = path.as_posix()
    normalized = posixpath.normpath(value)
    return "" if normalized == "." else normalized


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


def _binding_lines(
    spec: Spec,
    registry: SpecRegistry,
    *,
    root: Path | None,
) -> list[str]:
    bindings = _bindings_for_context(spec, registry, root=root)
    lines: list[str] = []
    for binding in bindings:
        omission = _binding_omission(binding, include_bindings=True)
        target = binding.target.path or ""
        if root is not None and target:
            target = _display_path_for_path(Path(target), root)
        if omission is None:
            note = " _(content not included)_"
        else:
            severity = "warning" if binding.validation_status == "warning" else "error"
            note = f" _({severity}: {omission}; content not included)_"
        lines.append(f"{binding.role}: `{target}`{note}")
    return lines


def _spec_payload(
    spec: Spec,
    registry: SpecRegistry,
    included_ids: set[str],
    root: Path | None,
    *,
    include_bindings: bool,
) -> dict[str, Any]:
    payload = {
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
    if not include_bindings:
        return payload

    binding_payloads = [
        _binding_payload(binding, include_bindings=include_bindings)
        for binding in _bindings_for_context(spec, registry, root=root)
    ]
    payload["bindings"] = binding_payloads
    payload["binding_diagnostics"] = [
        {
            "id": binding_payload["id"],
            "reason": binding_payload["omitted_reason"],
            "severity": binding_payload["validation"]["status"],
        }
        for binding_payload in binding_payloads
        if binding_payload["omitted_reason"] is not None
    ]
    return payload


def _bindings_for_context(
    spec: Spec, registry: SpecRegistry, *, root: Path | None
) -> tuple[Binding, ...]:
    result = bindings_for_spec(
        spec, registry.type_definition_for(spec), project_root=root
    )
    return result.bindings


def _binding_payload(
    binding: Binding,
    *,
    include_bindings: bool,
) -> dict[str, Any]:
    omission = _binding_omission(binding, include_bindings=include_bindings)
    return {
        "id": binding.id,
        "source_spec_id": binding.source_spec_id,
        "source_field": binding.source_field,
        "role": binding.role,
        "target": {
            "kind": binding.target.kind,
            "path": binding.target.path,
            "media_type": binding.target.media_type,
        },
        "binding_included": omission is None,
        "omitted_reason": omission,
        "artifact_included": False,
        "artifact_omitted_reason": "artifact_content_not_requested",
        "validation": {
            "status": binding.validation_status,
            "issues": [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "severity": issue.severity,
                }
                for issue in binding.validation_issues
            ],
        },
    }


def _binding_omission(
    binding: Binding,
    *,
    include_bindings: bool,
) -> BindingOmissionReason | None:
    if any(issue.code == "GROUNDED-BINDING-006" for issue in binding.validation_issues):
        return "unsupported_target_kind"
    if any(issue.code == "GROUNDED-BINDING-009" for issue in binding.validation_issues):
        return "missing_path"
    if binding.validation_status == "error":
        return "invalid_binding"
    if not include_bindings:
        return "include_bindings_not_requested"
    return None


def _display_path(spec: Spec, root: Path | None) -> str:
    return _display_path_for_path(spec.path, root)


def _display_path_for_path(path: Path, root: Path | None) -> str:
    if root is not None:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return path.as_posix()
