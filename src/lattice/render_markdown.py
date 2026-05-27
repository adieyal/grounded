from __future__ import annotations

from .models import Spec
from .registry import SpecRegistry
from .render_constants import GENERATED_HEADER
from .render_context import specs_by_type


def render_markdown(registry: SpecRegistry) -> str:
    lines = [
        GENERATED_HEADER,
        "",
        "# Project Memory",
        "",
        "This file is generated from Lattice canonical knowledge units.",
        "",
    ]
    for type_name, specs in specs_by_type(registry.active_specs).items():
        lines.extend([f"## {type_name.replace('_', ' ').title()}", ""])
        for spec in specs:
            lines.extend(_render_spec_summary(spec))
    return "\n".join(lines).rstrip() + "\n"


def render_llm_pack(registry: SpecRegistry) -> str:
    lines = [
        GENERATED_HEADER,
        "",
        "# Lattice LLM Context Pack",
        "",
        "Use these canonical knowledge units as the source of truth. Do not duplicate or invent competing facts.",
        "",
    ]
    for spec in sorted(registry.active_specs, key=lambda item: (item.kind, item.id)):
        summary = spec.description
        if spec.statement and spec.statement != spec.description:
            summary = f"{spec.description} {spec.statement}"
        lines.append(
            f"- `{spec.id}` ({spec.kind}, owner: {spec.owner or 'unknown'}): {summary}"
        )
        refs = ", ".join(spec.references)
        if refs:
            lines.append(f"  Links: {refs}")
    return "\n".join(lines).rstrip() + "\n"


def _render_spec_summary(spec: Spec) -> list[str]:
    lines = [
        f"### {spec.data.get('name', spec.id)}",
        "",
        f"- ID: `{spec.id}`",
        f"- Type: `{spec.kind}`",
    ]
    if spec.owner:
        lines.append(f"- Owner: `{spec.owner}`")
    if spec.description:
        lines.extend(["", spec.description])
    if spec.statement and spec.statement != spec.description:
        lines.extend(["", spec.statement])
    refs = ", ".join(f"`{ref}`" for ref in spec.references)
    if refs:
        lines.extend(["", f"Links: {refs}"])
    lines.append("")
    return lines
