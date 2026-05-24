from __future__ import annotations

import json
from pathlib import Path

from .models import LatticeConfig
from .registry import SpecRegistry
from .render_assets import default_css, render_css, render_link_component
from .render_constants import CSS_FILENAME, GENERATED_HEADER, LINK_COMPONENT_FILENAME, SEARCH_FILENAME
from .render_context import (
    base_context,
    json_for_html_script,
    primary_documentation_specs,
    specs_by_type,
    template_environment,
)
from .render_display import (
    concept_sections,
    detail_sections,
    display_fields,
    display_name,
    display_value,
    enum_values,
    field_anchor,
    field_label,
    field_type_display,
    field_type_target,
    lattice_link,
    page_component,
    type_nav_label,
    type_tone,
    value_type_name,
    visible_link_nodes,
)
from .render_graph import (
    build_search_index,
    flatten_search_value,
    lattice_key,
    lattice_registry_for,
    outgoing_links_for,
)
from .render_markdown import render_llm_pack, render_markdown
from .render_outputs import RenderedSite
from .render_paths import href_for, slugify, unit_output_path


def render_all(
    config: LatticeConfig, registry: SpecRegistry, *, check: bool = False
) -> list[str]:
    site = build_rendered_site(config, registry)

    if check:
        return site.stale_paths()

    site.write()
    return []


def prune_obsolete_outputs(config: LatticeConfig, expected: set[Path]) -> None:
    units_dir = config.generated_docs_dir / "units"
    if not units_dir.exists():
        return

    for path in units_dir.glob("*.html"):
        if path not in expected:
            path.unlink()


def build_site(config: LatticeConfig, registry: SpecRegistry) -> dict[Path, str]:
    return build_rendered_site(config, registry).outputs


def build_rendered_site(config: LatticeConfig, registry: SpecRegistry) -> RenderedSite:
    index_path = config.generated_docs_dir / "project-memory.html"
    background_path = config.generated_docs_dir / "lattice-background.html"

    graph = lattice_registry_for(config, registry, index_path)
    primary_specs = primary_documentation_specs(registry)
    primary_ids = {spec.id for spec in primary_specs}
    background_specs = [
        spec for spec in registry.active_specs if spec.id not in primary_ids
    ]

    env = template_environment(config)
    available_templates = set(env.list_templates())

    context = base_context(
        config,
        registry,
        graph,
        index_path,
        specs=primary_specs,
        search_specs=primary_specs,
    )
    background_context = base_context(
        config,
        registry,
        lattice_registry_for(config, registry, background_path),
        background_path,
        specs=background_specs,
        search_specs=primary_specs,
    )
    search_index = build_search_index(config, registry, graph, specs=primary_specs)

    site = RenderedSite(config=config)

    site.add(
        config.generated_docs_dir / "project-memory.md",
        render_markdown(registry),
        owner="project-memory markdown",
    )
    site.add(
        config.generated_docs_dir / "project-memory.html",
        env.get_template("index.html.j2").render(
            **context,
            background_href=href_for(index_path, background_path),
        ),
        owner="project-memory html",
    )
    site.add(
        background_path,
        env.get_template("background.html.j2").render(
            **background_context,
            main_href=href_for(background_path, index_path),
        ),
        owner="background page",
    )
    site.add(
        config.generated_docs_dir / CSS_FILENAME,
        render_css(config),
        owner=CSS_FILENAME,
    )
    site.add(
        config.generated_docs_dir / LINK_COMPONENT_FILENAME,
        render_link_component(),
        owner=LINK_COMPONENT_FILENAME,
    )
    site.add(
        config.search_index_path,
        json.dumps(search_index, indent=2, sort_keys=True) + "\n",
        owner=SEARCH_FILENAME,
    )
    site.add(
        config.generated_llm_dir / "context-pack.md",
        render_llm_pack(registry),
        owner="LLM context pack",
    )

    for spec in registry.active_specs:
        output_path = unit_output_path(config, spec)
        unit_graph = lattice_registry_for(config, registry, output_path)
        nav_specs = primary_specs if spec.id in primary_ids else background_specs
        unit_context = base_context(
            config,
            registry,
            unit_graph,
            output_path,
            specs=nav_specs,
            search_specs=primary_specs,
        )
        type_def = registry.type_definition_for(spec)
        template_name = type_def.renderer if type_def else "unit.html.j2"
        if template_name not in available_templates:
            template_name = "unit.html.j2"
        render_context = dict(unit_context)
        render_context.update(
            {
                "current_spec": spec,
                "spec": spec,
                "data": spec.data,
                "backlinks": unit_graph[lattice_key(spec)].get("backlinks", []),
                "outgoing": outgoing_links_for(spec, registry, unit_graph),
            }
        )
        site.add(
            output_path,
            env.get_template(template_name).render(**render_context),
            owner=f"{spec.kind}:{spec.id}",
        )

    return site


__all__ = [
    "GENERATED_HEADER",
    "CSS_FILENAME",
    "LINK_COMPONENT_FILENAME",
    "SEARCH_FILENAME",
    "RenderedSite",
    "base_context",
    "build_rendered_site",
    "build_search_index",
    "build_site",
    "concept_sections",
    "default_css",
    "detail_sections",
    "display_fields",
    "display_name",
    "display_value",
    "enum_values",
    "field_anchor",
    "field_label",
    "field_type_display",
    "field_type_target",
    "flatten_search_value",
    "href_for",
    "json_for_html_script",
    "lattice_key",
    "lattice_link",
    "lattice_registry_for",
    "outgoing_links_for",
    "page_component",
    "primary_documentation_specs",
    "prune_obsolete_outputs",
    "render_all",
    "render_css",
    "render_link_component",
    "render_llm_pack",
    "render_markdown",
    "slugify",
    "specs_by_type",
    "template_environment",
    "type_nav_label",
    "type_tone",
    "unit_output_path",
    "value_type_name",
    "visible_link_nodes",
]
