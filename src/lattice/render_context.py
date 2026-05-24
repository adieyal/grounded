from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import (
    ChoiceLoader,
    DictLoader,
    Environment,
    FileSystemLoader,
    select_autoescape,
)

from .models import LatticeConfig, Spec
from .registry import SpecRegistry
from .render_constants import CSS_FILENAME, GENERATED_HEADER, LINK_COMPONENT_FILENAME
from .render_display import (
    concept_sections,
    detail_sections,
    display_fields,
    display_name,
    enum_values,
    field_anchor,
    field_label,
    field_type_display,
    lattice_link,
    page_component,
    type_nav_label,
    type_tone,
    visible_link_nodes,
)
from .render_graph import build_search_index
from .render_paths import href_for, unit_output_path
from .render_templates import DEFAULT_TEMPLATES


def json_for_html_script(value: object) -> str:
    return (
        json.dumps(value, sort_keys=True)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def template_environment(config: LatticeConfig) -> Environment:
    loaders = []
    if config.templates_dir.exists():
        loaders.append(FileSystemLoader(str(config.templates_dir)))
    loaders.append(DictLoader(DEFAULT_TEMPLATES))
    env = Environment(
        loader=ChoiceLoader(loaders), autoescape=select_autoescape(("html", "j2"))
    )
    env.filters["field_label"] = field_label
    env.filters["as_json"] = lambda value: json.dumps(value, indent=2, sort_keys=True)
    env.globals["display_fields"] = display_fields
    env.globals["detail_sections"] = detail_sections
    env.globals["concept_sections"] = concept_sections
    env.globals["field_anchor"] = field_anchor
    env.globals["display_name"] = display_name
    env.globals["field_type_display"] = field_type_display
    env.globals["enum_values"] = enum_values
    env.globals["page_component"] = page_component
    env.globals["type_tone"] = type_tone
    env.globals["type_nav_label"] = type_nav_label
    env.globals["visible_link_nodes"] = visible_link_nodes
    return env


def primary_documentation_specs(registry: SpecRegistry) -> list[Spec]:
    primary = [
        spec for spec in registry.active_specs if spec.owner not in {"lattice", "project"}
    ]
    return sorted(primary or registry.active_specs, key=lambda item: (item.kind, item.id))


def base_context(
    config: LatticeConfig,
    registry: SpecRegistry,
    graph: dict[str, dict[str, Any]],
    output_path: Path,
    *,
    specs: list[Spec] | None = None,
    search_specs: list[Spec] | None = None,
) -> dict[str, Any]:
    visible_specs = sorted(
        specs if specs is not None else registry.active_specs,
        key=lambda item: (item.kind, item.id),
    )
    indexed_specs = search_specs if search_specs is not None else visible_specs

    return {
        "generated_header": GENERATED_HEADER,
        "registry": registry,
        "specs": visible_specs,
        "by_type": specs_by_type(visible_specs),
        "type_counts": Counter(spec.kind for spec in visible_specs),
        "lattice_registry": graph,
        "lattice_registry_json": json_for_html_script(graph),
        "search_index_json": json_for_html_script(
            build_search_index(config, registry, graph, specs=indexed_specs)
        ),
        "docs_title": config.docs_title,
        "docs_eyebrow": config.docs_eyebrow,
        "docs_description": config.docs_description,
        "docs_nav_label": config.docs_nav_label,
        "docs_background_title": config.docs_background_title,
        "docs_background_description": config.docs_background_description,
        "css_href": href_for(output_path, config.generated_docs_dir / CSS_FILENAME),
        "docs_home_href": href_for(
            output_path, config.generated_docs_dir / "project-memory.html"
        ),
        "link_component_href": href_for(
            output_path, config.generated_docs_dir / LINK_COMPONENT_FILENAME
        ),
        "unit_href": lambda spec: href_for(output_path, unit_output_path(config, spec)),
        "lattice_link": lattice_link,
        "current_spec": None,
    }


def specs_by_type(specs: list[Spec]) -> dict[str, list[Spec]]:
    by_type: dict[str, list[Spec]] = {}
    for spec in specs:
        by_type.setdefault(spec.kind, []).append(spec)
    return {
        key: sorted(value, key=lambda spec: spec.id)
        for key, value in sorted(by_type.items())
    }
