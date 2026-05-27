---
last_updated: 2026-05-27
---

# Lattice

Lattice is executable project memory: strongly typed knowledge units, linked
into a validated project graph.

Every durable project fact should have one canonical owner. Generated docs,
LLM context packs, audited artifacts, and tests should point back to that owner
instead of duplicating the idea in prose. Drift is a bug.

## MVP Commands

```bash
lattice init
lattice validate
lattice verify
lattice render --check
lattice audit
```

See [CHANGELOG.md](CHANGELOG.md) for release notes starting with `0.3.0`.

## Core Ideology

- A fact is authored once.
- Every fact is a typed knowledge unit derived from the core parent shape.
- Every knowledge unit has a description explaining what it is and what it is
  used for.
- Other artifacts reference it by stable ID.
- Type-specific JSON Schemas validate unit shape.
- Optional verification units run project-specific commands.
- Human docs and LLM context are generated views.
- Slice docs can present scoped subsets of the graph with their own metadata,
  index template, and stylesheet.
- Rendering is template-based and overrideable.
- Search is generated from the same registry as links and backlinks.
- Validation detects stale views, broken references, and coverage drift.
- Redundant project knowledge is suspicious until ownership is clear.

## Current Features

- `knowledge_unit` is the shared base shape. Each unit requires `id`, `name`,
  `owner`, `status`, and `description`.
- Core built-in kinds include `domain_object`, `enum`, `schema_gap`,
  `verification`, and `slice`.
- Project registries can define richer kinds in `registry/spec-types.json`
  without changing Lattice source code.
- Generated docs use `index.html` as the default entry page.
- Slice units render scoped documentation pages at
  `slices/<slug>/index.html`; each slice can declare its own `description`,
  explicit `members`, optional `index_template`, and optional `style_path`.
- Prose fields support constrained inline rich text: `[[SPEC-ID]]`,
  `[[SPEC-ID|label]]`, `[[SPEC-ID#fragment|label]]`, and
  `[[tag:name|label]]` render as safe internal links, while linked spec IDs
  participate in validation and backlinks.
- Generated docs include compact list components for dense linked
  name-and-description rows: `lattice-compact-list` and
  `lattice-compact-item`.
- Generated docs expose reusable Lit components that consume bundled design
  tokens, including `lattice-doc-header`, `lattice-section`,
  `lattice-pill-link-list`, `lattice-detail-list`, and `lattice-detail-row`.
- Project templates can extend reusable bundled templates such as
  `unit-core.html.j2` and `slice-index.html.j2`.
- Project styles can override the packaged stylesheet through the configured
  `styles_dir`.
- Verification units can run project-specific commands during `lattice verify`.

## Rich Text

Use constrained inline rich text inside prose fields such as `description`,
`summary`, `decision`, `definition`, `gap`, `suggested_improvement`, and field
descriptions:

```text
[[SPEC-ID]]
[[SPEC-ID|custom label]]
[[SPEC-ID#fragment|field label]]
[[tag:planned|planned work]]
`inline code`
**strong text**
_emphasis_
```

Spec links are validated and become graph references. Tag links render as tag
links but do not create spec references. Raw HTML is escaped.

## Extension Policy

Do not directly edit bundled Lattice templates, validation code, or rendering
functions to express project-specific behavior. Extend or override them instead:

- Add or refine kinds in the configured type registry.
- Add JSON Schemas through type definitions when a kind needs stricter shape.
- Add project templates under the configured `renderers/templates` directory and
  extend the reusable core templates.
- Use slice-level `index_template` and `style_path` for slice-specific pages.
- Put project-specific checks in `verification` units rather than in templates
  or renderer code.
- Change presentation through the configured `styles_dir` and design tokens.

## Project Layout

```text
lattice.yml
.lattice/
  specs/
  registry/
  schemas/
  templates/
  renderers/
    templates/
  generated/
    docs/
    llm/
```

`lattice init` creates this layout.
Use `lattice init --lattice-dir path/to/memory` to choose a different project
directory.
Use `lattice init --update-agents` to add a Lattice section to `AGENTS.md`.
