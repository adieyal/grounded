from __future__ import annotations

from .models import Spec
from .registry import SpecRegistry
from .render_constants import GENERATED_HEADER
from .render_context import specs_by_type
from .rich_text import rich_text_plain


def render_markdown(registry: SpecRegistry) -> str:
    lines = [
        GENERATED_HEADER,
        "",
        "# Project Memory",
        "",
        "This file is generated from Grounded canonical specs.",
        "",
    ]
    for type_name, specs in specs_by_type(registry.active_specs).items():
        lines.extend([f"## {type_name.replace('_', ' ').title()}", ""])
        for spec in specs:
            lines.extend(_render_spec_summary(spec, registry))
    return "\n".join(lines).rstrip() + "\n"


def render_llm_pack(registry: SpecRegistry) -> str:
    lines = [
        GENERATED_HEADER,
        "",
        "# Grounded LLM Context Pack",
        "",
        "Use these canonical specs as the source of truth. Do not duplicate or invent competing facts.",
        "",
    ]
    for spec in sorted(registry.active_specs, key=lambda item: (item.kind, item.id)):
        summary = rich_text_plain(spec.description, registry)
        if spec.statement and spec.statement != spec.description:
            summary = f"{summary} {rich_text_plain(spec.statement, registry)}"
        lines.append(
            f"- `{spec.id}` ({spec.kind}, owner: {spec.owner or 'unknown'}): {summary}"
        )
        refs = ", ".join(spec.references)
        if refs:
            lines.append(f"  Links: {refs}")
        for line in _typed_edge_lines(spec, registry):
            lines.append(f"  {line}")
    return "\n".join(lines).rstrip() + "\n"


def _render_spec_summary(spec: Spec, registry: SpecRegistry) -> list[str]:
    lines = [
        f"### {spec.data.get('name', spec.id)}",
        "",
        f"- ID: `{spec.id}`",
        f"- Type: `{spec.kind}`",
    ]
    if spec.owner:
        lines.append(f"- Owner: `{spec.owner}`")
    if spec.description:
        lines.extend(["", rich_text_plain(spec.description, registry)])
    if spec.statement and spec.statement != spec.description:
        lines.extend(["", rich_text_plain(spec.statement, registry)])
    refs = ", ".join(f"`{ref}`" for ref in spec.references)
    if refs:
        lines.extend(["", f"Links: {refs}"])
    edge_lines = _typed_edge_lines(spec, registry, code=True)
    if edge_lines:
        lines.extend(["", *edge_lines])
    lines.append("")
    return lines


def _typed_edge_lines(
    spec: Spec, registry: SpecRegistry, *, code: bool = False
) -> list[str]:
    outgoing = [
        _edge_display(edge.edge_type, "->", edge.target_id, code=code)
        for edge in registry.outgoing_edges_for(spec.id)
        if edge.target_id in registry.by_id
    ]
    incoming = [
        _edge_display(edge.edge_type, "<-", edge.source_id, code=code)
        for edge in registry.incoming_edges_for(spec.id)
        if edge.source_id in registry.by_id
    ]
    lines: list[str] = []
    if outgoing:
        lines.append(f"Edges: {', '.join(outgoing)}")
    if incoming:
        lines.append(f"Incoming edges: {', '.join(incoming)}")
    return lines


def _edge_display(edge_type: str, direction: str, target_id: str, *, code: bool) -> str:
    if code:
        return f"`{edge_type}` {direction} `{target_id}`"
    return f"{edge_type} {direction} {target_id}"
