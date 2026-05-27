from __future__ import annotations

DEFAULT_TEMPLATES: dict[str, str] = {
    "shell.html.j2": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{% block title %}{{ docs_title }}{% endblock %}</title>
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
    </lattice-top-bar>
    <lattice-sidebar slot="nav" aria-label="Knowledge units">
      {% for type_name, units in by_type.items() %}
      <lattice-nav-group>
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
  <p slot="actions" class="background-link"><a href="{{ background_href }}">Lattice background and generated metadata</a></p>
</lattice-page-hero>
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
  <p slot="actions" class="background-link"><a href="{{ main_href }}">Back to {{ docs_title }}</a></p>
</lattice-page-hero>
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
    {% set rows = display_fields(spec) %}
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
{% block after_fields %}
{% set values = enum_values(spec) %}
{% if values %}
<lattice-unit-section slot="before-context">
  <lattice-section-heading>Values</lattice-section-heading>
  <div class="allowed-values enum-values">
    {% for value in values %}<span class="tag t-type field-value">{{ value }}</span>{% endfor %}
  </div>
</lattice-unit-section>
{% endif %}
{% endblock %}
""",
    "domain_object.html.j2": """{% extends "unit.html.j2" %}""",
    "schema_gap.html.j2": """{% extends "unit.html.j2" %}""",
    "verification.html.j2": """{% extends "unit.html.j2" %}""",
}
