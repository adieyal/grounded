from __future__ import annotations

DEFAULT_TEMPLATES: dict[str, str] = {
    "shell.html.j2": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{% block title %}{{ docs_title }}{% endblock %}</title>
  <script>
    (() => {
      try {
        const theme = window.localStorage.getItem("lattice-theme");
        if (theme === "light" || theme === "dark") {
          document.documentElement.dataset.theme = theme;
        }
      } catch {}
    })();
  </script>
  <link rel="stylesheet" href="{{ css_href }}" />
  {% if extra_css_href %}<link rel="stylesheet" href="{{ extra_css_href }}" />{% endif %}
  <script type="module" src="{{ link_component_href }}"></script>
</head>
<body>
  <script type="application/json" id="lattice-registry">{{ lattice_registry_json | safe }}</script>
  <script type="application/json" id="lattice-search-index">{{ search_index_json | safe }}</script>
  <script type="application/json" id="lattice-tag-index">{{ tag_index_json | safe }}</script>
  <lattice-docs-app>
    <lattice-top-bar slot="top" home-href="{{ docs_home_href }}" label="{{ docs_nav_label }}">
      <lattice-search></lattice-search>
      <lattice-theme-toggle></lattice-theme-toggle>
    </lattice-top-bar>
    <lattice-sidebar slot="nav" aria-label="Knowledge units">
      <lattice-nav-group>
        <span slot="label">Views</span>
        <lattice-nav-item tone="flow"><a class="plain-nav-link" href="{{ docs_home_href }}">Overview</a></lattice-nav-item>
        <lattice-nav-item tone="flow"><a class="plain-nav-link" href="{{ document_graph_href }}">Document Graph</a></lattice-nav-item>
        <lattice-nav-item tone="flow"><a class="plain-nav-link" href="{{ artifact_index_href }}">Artifacts</a></lattice-nav-item>
        <lattice-nav-item tone="meta"><a class="plain-nav-link" href="{{ background_href }}">Background</a></lattice-nav-item>
      </lattice-nav-group>
      {% for type_name, units in by_type.items() %}
      <lattice-nav-group{% if current_spec and current_spec.kind == type_name %} open{% endif %}>
        <span slot="label">{{ type_nav_label(type_name) }}</span>
        {% for nav_spec in units %}
        <lattice-nav-item tone="{{ type_tone(nav_spec.kind) }}"{% if current_spec and current_spec.id == nav_spec.id %} active{% endif %}>
          {{ lattice_link(nav_spec.kind, nav_spec.id, display_name(nav_spec), "nav") | safe }}
        </lattice-nav-item>
        {% endfor %}
      </lattice-nav-group>
      {% endfor %}
    </lattice-sidebar>
    <lattice-main slot="main" class="pd-body">
      {% block content %}{% endblock %}
    </lattice-main>
  </lattice-docs-app>
</body>
</html>
""",
    "index.html.j2": """{% extends "shell.html.j2" %}
{% block content %}
<lattice-index-page>
<lattice-page-hero>
  <span slot="eyebrow">{{ docs_eyebrow }}</span>
  <span slot="title">{{ docs_title }}</span>
  <span slot="description">{{ docs_description }}</span>
  <p slot="actions" class="background-link"><a href="{{ document_graph_href }}">Explore the documentation graph</a> <a href="{{ artifact_index_href }}">Generated artifacts</a> <a href="{{ background_href }}">Background registry</a></p>
</lattice-page-hero>
{% set docs = generated_documents(registry) %}
{% if docs %}
<section class="story-band">
  <div>
    <p class="story-kicker">Generated views</p>
    <h2>These files are projections over Lattice specs.</h2>
    <p>Start with the documents, then follow each document into the sections, source specs, and governed assets that explain why the page exists.</p>
  </div>
  <div class="artifact-grid">
  {% for doc in docs %}
    <article class="artifact-card">
      <p class="artifact-path">{{ field_value(doc, "output_path") }}</p>
      <h3>{{ lattice_link(doc.kind, doc.id, display_name(doc), "plain") | safe }}</h3>
      <p>{{ rich_text(field_value(doc, "purpose", doc.description), registry) | safe }}</p>
      <div class="mini-metrics">
        <span>{{ list_values(doc, "section_refs") | length }} sections</span>
        <span>{{ field_value(doc, "write_mode", "protected_block") }}</span>
      </div>
    </article>
  {% endfor %}
  </div>
</section>
{% endif %}
{% set story_specs = primary_story_specs(registry) %}
{% if story_specs %}
<lattice-unit-section aria-labelledby="story-specs-title">
  <lattice-section-heading divider id="story-specs-title">What The Graph Says</lattice-section-heading>
  <div class="pd-cards semantic-cards">
  {% for spec in story_specs %}
    <lattice-unit-card>
      <h3 class="pd-card-name nm-{{ type_tone(spec.kind) }}">{{ lattice_link(spec.kind, spec.id, display_name(spec), "card-title") | safe }}</h3>
      <p class="pd-card-desc">{{ rich_text(primary_statement(spec), registry) | safe }}</p>
      <div class="pd-card-foot"><span class="tag t-{{ type_tone(spec.kind) }}">{{ spec.kind }}</span></div>
    </lattice-unit-card>
  {% endfor %}
  </div>
</lattice-unit-section>
{% endif %}
{% for type_name, units in by_type.items() %}
<lattice-unit-section aria-labelledby="{{ type_name }}-title">
  <lattice-section-heading divider id="{{ type_name }}-title">{{ type_nav_label(type_name) }}</lattice-section-heading>
  <div class="pd-cards">
  {% for spec in units %}
    <lattice-unit-card>
      <h3 class="pd-card-name nm-{{ type_tone(spec.kind) }}">{{ lattice_link(spec.kind, spec.id, display_name(spec), "card-title") | safe }}</h3>
      <p class="pd-card-desc">{{ rich_text(spec.description, registry) | safe }}</p>
      <div class="pd-card-foot"><span class="tag t-{{ type_tone(spec.kind) }}">{{ spec.kind }}</span></div>
    </lattice-unit-card>
  {% endfor %}
  </div>
</lattice-unit-section>
{% endfor %}
</lattice-index-page>
{% endblock %}
""",
    "background.html.j2": """{% extends "shell.html.j2" %}
{% block title %}{{ docs_background_title }} · {{ docs_title }}{% endblock %}
{% block content %}
<lattice-background-page>
<lattice-page-hero>
  <span slot="eyebrow">Background</span>
  <span slot="title">{{ docs_background_title }}</span>
  <span slot="description">{{ docs_background_description }}</span>
  <p slot="actions" class="background-link"><a href="{{ main_href }}">Back to {{ docs_title }}</a> <a href="{{ document_graph_href }}">Document graph</a></p>
</lattice-page-hero>
<section class="story-band">
  <div>
    <p class="story-kicker">Metamodel layer</p>
    <h2>Background specs explain the machinery behind the project docs.</h2>
    <p>This view keeps Lattice core definitions, guardrails, and support specs available without forcing them to compete with the primary project narrative.</p>
  </div>
  <div class="metric-strip">
  {% for type_name, count in type_counts.items() %}
    <span><strong>{{ count }}</strong>{{ type_nav_label(type_name) }}</span>
  {% endfor %}
  </div>
</section>
{% for type_name, units in by_type.items() %}
<lattice-unit-section aria-labelledby="{{ type_name }}-background-title">
  <lattice-section-heading divider id="{{ type_name }}-background-title">{{ type_nav_label(type_name) }}</lattice-section-heading>
  <div class="pd-cards">
  {% for spec in units %}
    <lattice-unit-card>
      <h3 class="pd-card-name nm-{{ type_tone(spec.kind) }}">{{ lattice_link(spec.kind, spec.id, display_name(spec), "card-title") | safe }}</h3>
      <p class="pd-card-desc">{{ rich_text(spec.description, registry) | safe }}</p>
      <div class="pd-card-foot"><span class="tag t-{{ type_tone(spec.kind) }}">{{ spec.kind }}</span></div>
    </lattice-unit-card>
  {% endfor %}
  </div>
</lattice-unit-section>
{% endfor %}
</lattice-background-page>
{% endblock %}
""",
    "unit-core.html.j2": """{% extends "shell.html.j2" %}
{% block title %}{{ data.name }} · Lattice{% endblock %}
{% block content %}
{% set page_tag = page_component(spec.kind) %}
<{{ page_tag }}>
<lattice-doc-header slot="hero">
  <span slot="eyebrow">{{ spec.kind | field_label }}</span>
  <span slot="title">{{ data.name }}</span>
  <span slot="lead">{{ rich_text(spec.description, registry) | safe }}</span>
  <lattice-copy-id slot="actions" value="{{ spec.id }}"></lattice-copy-id>
</lattice-doc-header>
{% set tags = tag_values(spec) %}
{% if tags %}
<div class="tag-panel">
  <lattice-section-heading>Tags</lattice-section-heading>
  <div class="tag-list">
    {% for tag in tags %}{{ lattice_link("tag", tag, tag, "tag") | safe }}{% endfor %}
  </div>
</div>
{% endif %}
<div slot="fields">
    {% block semantic_body %}
    {% set statement = primary_statement(spec) %}
    {% if statement %}
    <section class="semantic-lead-card">
      <p class="story-kicker">Source Meaning</p>
      <p>{{ rich_text(statement, registry) | safe }}</p>
    </section>
    {% endif %}
    {% endblock %}
    {% set rows = display_fields(spec) %}
    <details class="metadata-unit">
    <summary>Metadata fields</summary>
    <lattice-section-heading>Fields</lattice-section-heading>
    <lattice-field-table>
    <table class="pd-ft field-table">
      <thead>
        <tr>
          <th class="ft-num"></th>
          <th class="ft-name">Name</th>
          <th class="ft-type">Type</th>
          <th class="ft-req">Required</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
    {% for field in rows %}
      <tr class="field-row" id="{{ field_anchor(spec.id, field['name']) }}">
        <td class="ft-num field-index">{{ loop.index }}</td>
        <td class="ft-name field-name">{{ field["name"] }}</td>
        <td class="ft-type">{{ field_type_display(field["type"], registry) | safe }}</td>
        {% if field["required"] is sameas true %}
        <td class="ft-req"><span class="tag t-req field-required">required</span></td>
        {% elif field["required"] is sameas false %}
        <td class="ft-req"><span class="tag t-opt field-optional">optional</span></td>
        {% else %}
        <td class="ft-req"></td>
        {% endif %}
        <td class="ft-desc">
          <p class="field-description">{{ rich_text(field["description"], registry) | safe }}</p>
          {% if field["allowed_values"] %}
          <div class="allowed-values">
            <span>Allowed values:</span>
            {% for value in field["allowed_values"] %}<span class="tag t-type field-value">{{ value }}</span>{% endfor %}
          </div>
          {% endif %}
          {% if field["tags"] %}
          <div class="allowed-values">
            <span>Tags:</span>
            {% for tag in field["tags"] %}{{ lattice_link("tag", tag, tag, "tag") | safe }}{% endfor %}
          </div>
          {% endif %}
          {% if field["references"] %}
          <div class="allowed-values">
            <span>References:</span>
            {% for reference_id in field["references"] %}
              {% if reference_id in registry.by_id %}
                {% set reference = registry.by_id[reference_id] %}
                {{ lattice_link(reference.kind, reference.id, display_name(reference), "plain") | safe }}
              {% else %}
                <span class="tag t-type field-value">{{ reference_id }}</span>
              {% endif %}
            {% endfor %}
          </div>
          {% endif %}
        </td>
      </tr>
    {% else %}
      <tr class="field-row"><td class="ft-num field-index">0</td><td class="ft-name field-name">No display fields</td><td></td><td></td><td></td></tr>
    {% endfor %}
      </tbody>
    </table>
    </lattice-field-table>
    </details>
    {% set sections = detail_sections(spec) %}
    {% if sections %}
    <div class="detail-panels">
      {% for section in sections %}
      <section class="detail-panel">
        <h3>{{ section["title"] }}</h3>
        <ul>
          {% for item in section["items"] %}<li>{{ rich_text(item, registry) | safe }}</li>{% endfor %}
        </ul>
      </section>
      {% endfor %}
    </div>
    {% endif %}
    {% block after_detail_sections %}{% endblock %}
</div>
    {% block after_fields %}{% endblock %}
    {% for section in concept_sections(outgoing, backlinks, include_related=spec.kind != "business_entity") %}
    <lattice-concept-section slot="context" aria-labelledby="{{ section["role"] or "related" }}-concepts-title">
      <lattice-section-heading id="{{ section["role"] or "related" }}-concepts-title">{{ section["title"] }}</lattice-section-heading>
      {% for node in section["items"] %}
      <lattice-concept-card>
        <h3 class="pd-inv-name">{{ lattice_link(node.type, node.id, node.label, "plain") | safe }}</h3>
        <p class="pd-inv-desc">{{ rich_text(node.summary, registry) | safe }}</p>
      </lattice-concept-card>
      {% endfor %}
    </lattice-concept-section>
    {% endfor %}
    <lattice-links-panel slot="links">
      <lattice-section-heading>Links</lattice-section-heading>
      {% set visible_outgoing = visible_link_nodes(spec, outgoing) %}
      {% set visible_backlinks = visible_link_nodes(spec, backlinks) %}
      <div class="pd-links-row">
        <div class="pd-links-col">
          <h3 class="pd-links-head">Outgoing</h3>
          <div class="link-list">
            {% for node in visible_outgoing %}{{ lattice_link(node.type, node.id, node.label, "plain") | safe }}{% else %}<span class="tag t-opt">None</span>{% endfor %}
          </div>
        </div>
        <div class="pd-links-col">
          <h3 class="pd-links-head">Backlinks</h3>
          <div class="link-list">
            {% for node in visible_backlinks %}{{ lattice_link(node.type, node.id, node.label, "plain") | safe }}{% else %}<span class="tag t-opt">None</span>{% endfor %}
          </div>
        </div>
      </div>
    </lattice-links-panel>
    <lattice-raw-json slot="raw">
      <details class="raw-unit">
      <summary>Raw JSON</summary>
      <pre class="raw-data"><code>{{ data | as_json }}</code></pre>
      </details>
    </lattice-raw-json>
</{{ page_tag }}>
{% endblock %}
""",
    "unit.html.j2": """{% extends "unit-core.html.j2" %}""",
    "slice-index.html.j2": """{% extends "shell.html.j2" %}
{% block title %}{{ slice.data.name }} · {{ docs_title }}{% endblock %}
{% block content %}
<lattice-index-page>
<lattice-page-hero>
  <span slot="eyebrow">Slice</span>
  <span slot="title">{{ slice.data.name }}</span>
  <span slot="description">{{ rich_text(slice_description, registry) | safe }}</span>
  <p slot="actions" class="background-link"><a href="{{ docs_home_href }}">All project memory</a></p>
</lattice-page-hero>
{% for type_name, units in by_type.items() %}
<lattice-unit-section aria-labelledby="{{ type_name }}-slice-title">
  <lattice-section-heading divider id="{{ type_name }}-slice-title">{{ type_nav_label(type_name) }}</lattice-section-heading>
  <div class="pd-cards">
  {% for spec in units %}
    <lattice-unit-card>
      <h3 class="pd-card-name nm-{{ type_tone(spec.kind) }}">{{ lattice_link(spec.kind, spec.id, display_name(spec), "card-title") | safe }}</h3>
      <p class="pd-card-desc">{{ rich_text(spec.description, registry) | safe }}</p>
      <div class="pd-card-foot"><span class="tag t-{{ type_tone(spec.kind) }}">{{ spec.kind }}</span></div>
    </lattice-unit-card>
  {% endfor %}
  </div>
</lattice-unit-section>
{% endfor %}
</lattice-index-page>
{% endblock %}
""",
    "tag.html.j2": """{% extends "shell.html.j2" %}
{% block title %}{{ tag_name }} · Tags · {{ docs_title }}{% endblock %}
{% block content %}
<lattice-tag-page>
<lattice-page-hero>
  <span slot="eyebrow">Tag</span>
  <span slot="title">{{ tag_name }}</span>
  <span slot="description">{{ tag_count }} tagged element{% if tag_count != 1 %}s{% endif %}, grouped by type.</span>
  <p slot="actions" class="background-link"><a href="{{ docs_home_href }}">Back to {{ docs_title }}</a></p>
</lattice-page-hero>
{% for section in tag_sections %}
<lattice-unit-section>
  <lattice-section-heading divider>{{ section["title"] }}</lattice-section-heading>
  <lattice-compact-list>
  {% for item in section["items"] %}
    <lattice-compact-item>
      <span slot="name">{{ lattice_link(item["type"], item["id"], item["label"], "plain", item.get("fragment")) | safe }}</span>
      <span slot="description">{{ rich_text(item["summary"], registry) | safe }}</span>
    </lattice-compact-item>
  {% endfor %}
  </lattice-compact-list>
</lattice-unit-section>
{% endfor %}
</lattice-tag-page>
{% endblock %}
""",
    "enum.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Controlled Vocabulary</p>
  <p>{{ rich_text(primary_statement(spec), registry) | safe }}</p>
</section>
{% set values = enum_values(spec) %}
{% if values %}
<section class="semantic-section">
  <lattice-section-heading>Values</lattice-section-heading>
  <div class="allowed-values enum-values">
    {% for value in values %}<span class="tag t-type field-value">{{ value }}</span>{% endfor %}
  </div>
</section>
{% endif %}
{% endblock %}
""",
    "domain_object.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Domain Meaning</p>
  <p>{{ rich_text(primary_statement(spec), registry) | safe }}</p>
</section>
{% endblock %}
""",
    "generated_document.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card artifact-hero">
  <p class="story-kicker">Generated Document</p>
  <p>{{ rich_text(field_value(spec, "purpose", spec.description), registry) | safe }}</p>
  <div class="artifact-facts">
    <span><strong>Output</strong>{{ field_value(spec, "output_path") }}</span>
    <span><strong>Format</strong>{{ field_value(spec, "format") }}</span>
    <span><strong>Write mode</strong>{{ field_value(spec, "write_mode", "protected_block") }}</span>
    {% if field_value(spec, "audience") %}<span><strong>Audience</strong>{{ field_value(spec, "audience") }}</span>{% endif %}
  </div>
</section>
{% set sections = specs_for_refs(spec, registry, "section_refs") %}
{% if sections %}
<section class="semantic-section">
  <lattice-section-heading>Document Sections</lattice-section-heading>
  <ol class="timeline-list">
  {% for section in sections %}
    <li>
      <span class="timeline-number">{{ loop.index }}</span>
      <div>
        <h3>{{ lattice_link(section.kind, section.id, display_name(section), "plain") | safe }}</h3>
        <p>{{ rich_text(field_value(section, "intro", section.description), registry) | safe }}</p>
        <div class="mini-metrics">
          <span>{{ field_value(section, "renderer") }}</span>
          <span>{{ field_value(section, "content_mode") }}</span>
          <span>{{ list_values(section, "source_refs") | length }} sources</span>
        </div>
      </div>
    </li>
  {% endfor %}
  </ol>
</section>
{% endif %}
{% set sources = specs_for_refs(spec, registry, "source_refs") %}
{% if sources %}
<section class="semantic-section">
  <lattice-section-heading>Document Sources</lattice-section-heading>
  <lattice-compact-list>
  {% for source in sources %}
    <lattice-compact-item>
      <span slot="name">{{ lattice_link(source.kind, source.id, display_name(source), "plain") | safe }}</span>
      <span slot="description">{{ rich_text(primary_statement(source), registry) | safe }}</span>
    </lattice-compact-item>
  {% endfor %}
  </lattice-compact-list>
</section>
{% endif %}
{% endblock %}
""",
    "document_section.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Reusable Section</p>
  <p>{{ rich_text(field_value(spec, "intro", spec.description), registry) | safe }}</p>
  <div class="artifact-facts">
    <span><strong>Heading</strong>{{ field_value(spec, "heading") }}</span>
    <span><strong>Renderer</strong>{{ field_value(spec, "renderer") }}</span>
    <span><strong>Content mode</strong>{{ field_value(spec, "content_mode") }}</span>
    <span><strong>Order</strong>{{ field_value(spec, "order") }}</span>
  </div>
</section>
{% set sources = specs_for_refs(spec, registry, "source_refs") %}
{% if sources %}
<section class="semantic-section">
  <lattice-section-heading>Source Specs</lattice-section-heading>
  <lattice-compact-list>
  {% for source in sources %}
    <lattice-compact-item>
      <span slot="name">{{ lattice_link(source.kind, source.id, display_name(source), "plain") | safe }}</span>
      <span slot="description">{{ rich_text(primary_statement(source), registry) | safe }}</span>
    </lattice-compact-item>
  {% endfor %}
  </lattice-compact-list>
</section>
{% endif %}
{% set assets = specs_for_refs(spec, registry, "asset_refs") %}
{% if assets %}
<section class="semantic-section">
  <lattice-section-heading>Assets</lattice-section-heading>
  <div class="pd-cards semantic-cards">
  {% for asset in assets %}
    <lattice-unit-card>
      <h3 class="pd-card-name">{{ lattice_link(asset.kind, asset.id, display_name(asset), "card-title") | safe }}</h3>
      <p class="pd-card-desc">{{ field_value(asset, "path") }}</p>
    </lattice-unit-card>
  {% endfor %}
  </div>
</section>
{% endif %}
{% set consumers = specs_referencing(registry, spec.id, field="section_refs") %}
{% if consumers %}
<section class="semantic-section">
  <lattice-section-heading>Used By Documents</lattice-section-heading>
  <div class="link-list">
  {% for consumer in consumers %}{{ lattice_link(consumer.kind, consumer.id, display_name(consumer), "plain") | safe }}{% endfor %}
  </div>
</section>
{% endif %}
{% endblock %}
""",
    "documentation_set.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Documentation Set</p>
  <p>{{ rich_text(primary_statement(spec), registry) | safe }}</p>
  <div class="artifact-facts">
    <span><strong>Output root</strong>{{ field_value(spec, "default_output_dir") }}</span>
    <span><strong>Documents</strong>{{ list_values(spec, "document_refs") | length }}</span>
  </div>
</section>
{% set docs = specs_for_refs(spec, registry, "document_refs") %}
{% if docs %}
<section class="semantic-section">
  <lattice-section-heading>Documents In This Set</lattice-section-heading>
  <ol class="timeline-list">
  {% for doc in docs %}
    <li>
      <span class="timeline-number">{{ loop.index }}</span>
      <div>
        <h3>{{ lattice_link(doc.kind, doc.id, display_name(doc), "plain") | safe }}</h3>
        <p>{{ field_value(doc, "output_path") }}</p>
      </div>
    </li>
  {% endfor %}
  </ol>
</section>
{% endif %}
{% endblock %}
""",
    "asset.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Governed Asset</p>
  <p>{{ rich_text(primary_statement(spec), registry) | safe }}</p>
  <div class="artifact-facts">
    <span><strong>Path</strong>{{ field_value(spec, "path") }}</span>
    <span><strong>Kind</strong>{{ field_value(spec, "asset_kind") }}</span>
    <span><strong>Media</strong>{{ field_value(spec, "media_type") }}</span>
  </div>
  {% if field_value(spec, "alt") %}<p class="asset-alt"><strong>Alt text:</strong> {{ field_value(spec, "alt") }}</p>{% endif %}
</section>
{% set used_by = specs_for_refs(spec, registry, "used_by") %}
{% if used_by %}
<section class="semantic-section">
  <lattice-section-heading>Used By</lattice-section-heading>
  <div class="link-list">
  {% for target in used_by %}{{ lattice_link(target.kind, target.id, display_name(target), "plain") | safe }}{% endfor %}
  </div>
</section>
{% endif %}
{% endblock %}
""",
    "decision.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card decision-card">
  <p class="story-kicker">Decision</p>
  <p>{{ rich_text(field_value(spec, "decision"), registry) | safe }}</p>
</section>
{% set tests = specs_for_refs(spec, registry, "tests") %}
{% if tests %}
<section class="semantic-section">
  <lattice-section-heading>Proof Obligations</lattice-section-heading>
  <lattice-compact-list>
  {% for test in tests %}
    <lattice-compact-item>
      <span slot="name">{{ lattice_link(test.kind, test.id, display_name(test), "plain") | safe }}</span>
      <span slot="description">{{ rich_text(field_value(test, "test", test.description), registry) | safe }}</span>
    </lattice-compact-item>
  {% endfor %}
  </lattice-compact-list>
</section>
{% endif %}
{% endblock %}
""",
    "guardrail.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Guardrail</p>
  <p>{{ rich_text(primary_statement(spec), registry) | safe }}</p>
</section>
<section class="semantic-section fix-panel">
  <lattice-section-heading>How To Fix Drift</lattice-section-heading>
  <p>Update the source spec that owns the rule, regenerate the affected view, then run the validation/audit command named by the linked test binding or verification spec.</p>
</section>
{% set tests = specs_for_refs(spec, registry, "tests") %}
{% if tests %}
<section class="semantic-section">
  <lattice-section-heading>Checked By</lattice-section-heading>
  <div class="link-list">
  {% for test in tests %}{{ lattice_link(test.kind, test.id, display_name(test), "plain") | safe }}{% endfor %}
  </div>
</section>
{% endif %}
{% endblock %}
""",
    "test_binding.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Executable Proof</p>
  <p>{{ rich_text(field_value(spec, "test", spec.description), registry) | safe }}</p>
  <div class="artifact-facts">
    {% set target = specs_for_refs(spec, registry, "target") %}
    {% if target %}<span><strong>Target</strong>{{ lattice_link(target[0].kind, target[0].id, display_name(target[0]), "plain") | safe }}</span>{% endif %}
  </div>
</section>
{% endblock %}
""",
    "schema_gap.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Schema Gap</p>
  <p>{{ rich_text(field_value(spec, "gap"), registry) | safe }}</p>
</section>
<section class="semantic-section fix-panel">
  <lattice-section-heading>Suggested Improvement</lattice-section-heading>
  <p>{{ rich_text(field_value(spec, "suggested_improvement"), registry) | safe }}</p>
</section>
{% endblock %}
""",
    "verification.html.j2": """{% extends "unit.html.j2" %}
{% block semantic_body %}
<section class="semantic-lead-card">
  <p class="story-kicker">Verification</p>
  <p>{{ rich_text(primary_statement(spec), registry) | safe }}</p>
  <pre class="command-block"><code>{{ field_value(spec, "command") }}</code></pre>
</section>
{% endblock %}
""",
    "artifact-index.html.j2": """{% extends "shell.html.j2" %}
{% block title %}Generated Artifacts · {{ docs_title }}{% endblock %}
{% block content %}
<lattice-index-page>
<lattice-page-hero>
  <span slot="eyebrow">Artifacts</span>
  <span slot="title">Generated artifacts</span>
  <span slot="description">Every emitted documentation file should have an owning Lattice spec and a path readers can inspect.</span>
  <p slot="actions" class="background-link"><a href="{{ docs_home_href }}">Overview</a> <a href="{{ document_graph_href }}">Document graph</a></p>
</lattice-page-hero>
<lattice-unit-section>
  <lattice-section-heading divider>Artifact Manifest</lattice-section-heading>
  <lattice-compact-list>
  {% for artifact in document_artifacts(registry) %}
    <lattice-compact-item>
      <span slot="name">{{ lattice_link(artifact.spec.kind, artifact.spec.id, artifact.path, "plain") | safe }}</span>
      <span slot="description">{{ artifact.format }} · {{ artifact.write_mode }} · {{ artifact.section_count }} sections</span>
    </lattice-compact-item>
  {% endfor %}
  </lattice-compact-list>
</lattice-unit-section>
</lattice-index-page>
{% endblock %}
""",
    "document-graph.html.j2": """{% extends "shell.html.j2" %}
{% block title %}Document Graph · {{ docs_title }}{% endblock %}
{% block content %}
<lattice-index-page>
<lattice-page-hero>
  <span slot="eyebrow">Document Graph</span>
  <span slot="title">Docs are projections, not sources.</span>
  <span slot="description">Generated documents point to ordered sections. Sections point to durable source specs and governed assets.</span>
  <p slot="actions" class="background-link"><a href="{{ docs_home_href }}">Overview</a> <a href="{{ artifact_index_href }}">Artifacts</a></p>
</lattice-page-hero>
{% for doc in generated_documents(registry) %}
<lattice-unit-section>
  <lattice-section-heading divider>{{ field_value(doc, "output_path") }}</lattice-section-heading>
  <ol class="timeline-list">
  {% for section in specs_for_refs(doc, registry, "section_refs") %}
    <li>
      <span class="timeline-number">{{ loop.index }}</span>
      <div>
        <h3>{{ lattice_link(section.kind, section.id, display_name(section), "plain") | safe }}</h3>
        <p>{{ rich_text(field_value(section, "intro", section.description), registry) | safe }}</p>
        {% set sources = specs_for_refs(section, registry, "source_refs") %}
        {% if sources %}
        <div class="link-list source-links">
        {% for source in sources %}{{ lattice_link(source.kind, source.id, display_name(source), "plain") | safe }}{% endfor %}
        </div>
        {% endif %}
      </div>
    </li>
  {% endfor %}
  </ol>
</lattice-unit-section>
{% endfor %}
</lattice-index-page>
{% endblock %}
""",
}
