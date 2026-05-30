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
    lines.append("")
    return lines
