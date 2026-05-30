from __future__ import annotations

import json
from pathlib import Path

from .models import GroundedConfig
from .registry import SpecRegistry
from .render_assets import default_css, render_css, render_link_component
from .render_constants import (
    CSS_FILENAME,
    GENERATED_HEADER,
    INDEX_FILENAME,
    LINK_COMPONENT_FILENAME,
    SEARCH_FILENAME,
)
from .render_context import (
    base_context,
    json_for_html_script,
    primary_documentation_specs,
    specs_by_type,
    template_environment,
)
from .render_documents import generated_documents
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
    grounded_link,
    page_component,
    type_nav_label,
    type_tone,
    value_type_name,
    visible_link_nodes,
)
from .render_graph import (
    build_search_index,
    flatten_search_value,
    grounded_key,
    grounded_registry_for,
    graph_reference_ids_for,
    outgoing_links_for,
)
from .render_markdown import render_llm_pack, render_markdown
from .render_outputs import RenderedSite
from .render_paths import href_for, slugify, unit_output_path
from .render_slices import (
    SLICE_INDEX_TEMPLATE,
    slice_description,
    slice_members,
    slice_output_path,
    slice_specs,
    slice_style_output_path,
    slice_style_source,
    slice_template_name,
)
from .render_tags import tag_index_for, tag_output_path, tag_sections_for, tags_by_name


def render_all(
    config: GroundedConfig, registry: SpecRegistry, *, check: bool = False
) -> list[str]:
    site = build_rendered_site(config, registry)

    if check:
        return site.stale_paths()

    site.write()
    return []


def prune_obsolete_outputs(config: GroundedConfig, expected: set[Path]) -> None:
    units_dir = config.generated_docs_dir / "units"
    if not units_dir.exists():
        return

    for path in units_dir.glob("*.html"):
        if path not in expected:
            path.unlink()


def build_site(config: GroundedConfig, registry: SpecRegistry) -> dict[Path, str]:
    return build_rendered_site(config, registry).outputs


def build_rendered_site(config: GroundedConfig, registry: SpecRegistry) -> RenderedSite:
    index_path = config.generated_docs_dir / INDEX_FILENAME
    background_path = config.generated_docs_dir / "grounded-background.html"
    artifact_index_path = config.generated_docs_dir / "artifact-index.html"
    document_graph_path = config.generated_docs_dir / "document-graph.html"

    graph = grounded_registry_for(config, registry, index_path)
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
        grounded_registry_for(config, registry, background_path),
        background_path,
        specs=background_specs,
        search_specs=primary_specs,
    )
    search_index = build_search_index(config, registry, graph, specs=primary_specs)
    tag_groups = tags_by_name(registry.active_specs, config, index_path)

    site = RenderedSite(config=config)

    site.add(
        config.generated_docs_dir / "project-memory.md",
        render_markdown(registry),
        owner="project-memory markdown",
    )
    site.add(
        config.generated_docs_dir / INDEX_FILENAME,
        env.get_template("index.html.j2").render(**context),
        owner="index html",
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
        document_graph_path,
        env.get_template("document-graph.html.j2").render(
            **base_context(
                config,
                registry,
                grounded_registry_for(config, registry, document_graph_path),
                document_graph_path,
                specs=primary_specs,
                search_specs=primary_specs,
            )
        ),
        owner="document graph page",
    )
    site.add(
        artifact_index_path,
        env.get_template("artifact-index.html.j2").render(
            **base_context(
                config,
                registry,
                grounded_registry_for(config, registry, artifact_index_path),
                artifact_index_path,
                specs=primary_specs,
                search_specs=primary_specs,
            )
        ),
        owner="artifact index page",
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

    for document in generated_documents(config, registry):
        if document.write_mode == "full_file":
            site.add(document.path, document.content, owner=document.spec.id)
        else:
            site.add_block(
                document.path,
                document.spec.id,
                document.content,
                owner=document.spec.id,
            )

    for tag, tagged_specs in tag_groups.items():
        tag_path = tag_output_path(config, tag)
        tag_context = base_context(
            config,
            registry,
            grounded_registry_for(config, registry, tag_path),
            tag_path,
            specs=registry.active_specs,
            search_specs=primary_specs,
        )
        tag_render_context = dict(tag_context)
        tag_render_context.update(
            {
                "tag_name": tag,
                "tag_count": len(tagged_specs),
                "tag_sections": tag_sections_for(tag, tagged_specs, config, tag_path),
                "current_spec": None,
            }
        )
        site.add(
            tag_path,
            env.get_template("tag.html.j2").render(**tag_render_context),
            owner=f"tag:{tag}",
        )

    for slice_spec in slice_specs(registry):
        members = slice_members(slice_spec, registry)
        output_path = slice_output_path(config, slice_spec)
        slice_graph = grounded_registry_for(config, registry, output_path, specs=members)
        slice_context = base_context(
            config,
            registry,
            slice_graph,
            output_path,
            specs=members,
            search_specs=members,
            tag_specs=members,
        )
        slice_render_context = dict(slice_context)
        style_source = slice_style_source(config, slice_spec)
        style_output_path = slice_style_output_path(config, slice_spec)
        if (
            style_source is not None
            and style_output_path is not None
            and style_source.exists()
        ):
            site.add(
                style_output_path,
                style_source.read_text(encoding="utf-8"),
                owner=f"slice-style:{slice_spec.id}",
            )
            slice_render_context["extra_css_href"] = href_for(
                output_path, style_output_path
            )

        template_name = slice_template_name(slice_spec)
        if template_name not in available_templates:
            template_name = SLICE_INDEX_TEMPLATE
        slice_render_context.update(
            {
                "slice": slice_spec,
                "slice_members": members,
                "slice_description": slice_description(slice_spec),
                "current_spec": None,
            }
        )
        site.add(
            output_path,
            env.get_template(template_name).render(**slice_render_context),
            owner=f"slice:{slice_spec.id}",
        )

    for spec in registry.active_specs:
        output_path = unit_output_path(config, spec)
        unit_graph = grounded_registry_for(config, registry, output_path)
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
                "backlinks": unit_graph[grounded_key(spec)].get("backlinks", []),
                "outgoing": outgoing_links_for(spec, registry, unit_graph),
            }
        )
        site.add(
            output_path,
            env.get_template(template_name).render(**render_context),
            owner=f"{spec.kind}:{spec.id}",
        )

    site.add(
        config.generated_docs_dir.parent / "manifest.json",
        site.manifest_json(),
        owner="generated artifact manifest",
    )

    return site


__all__ = [
    "GENERATED_HEADER",
    "CSS_FILENAME",
    "INDEX_FILENAME",
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
    "grounded_key",
    "grounded_link",
    "grounded_registry_for",
    "graph_reference_ids_for",
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
    "slice_description",
    "slice_members",
    "slice_output_path",
    "slice_specs",
    "slice_style_output_path",
    "slice_style_source",
    "slice_template_name",
    "specs_by_type",
    "template_environment",
    "type_nav_label",
    "type_tone",
    "tag_index_for",
    "tag_output_path",
    "tag_sections_for",
    "tags_by_name",
    "unit_output_path",
    "value_type_name",
    "visible_link_nodes",
]
