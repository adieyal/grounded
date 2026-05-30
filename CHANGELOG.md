---
last_updated: 2026-05-30
---

# Changelog

All notable Grounded changes are recorded here starting with `0.3.0`.

## 1.0.0 - 2026-05-30

- Added documentation-graph registry types for generated documents, document
  sections, documentation sets, and governed assets.
- Added generated Markdown protected blocks and a generated artifact manifest
  so root docs such as `README.md` can migrate toward Grounded ownership.
- Added full-file generated document write mode so mature documentation graph
  outputs can own their entire target path.
- Converted `README.md` and public Markdown files under `docs/` to full-file
  generated outputs owned by `generated_document` specs.
- Added an audit guardrail requiring public Markdown documentation to be
  managed by the generated-document graph.
- Redesigned generated HTML documentation around semantic templates for
  generated documents, sections, documentation sets, assets, decisions,
  guardrails, test bindings, schema gaps, verification specs, enums, and domain
  objects so pages explain meaning and graph ownership before raw metadata.
- Added generated document graph and artifact index pages to make generated
  documentation provenance inspectable.
- Prepared the package for PyPI publication with PyPI-facing project metadata,
  Apache-2.0 license metadata, sdist inclusion rules, a typed-package marker,
  ignored build artifacts, and a trusted-publishing GitHub Actions workflow.
- Bumped the package to the first major release version, `1.0.0`.

## 0.13.0 - 2026-05-30

- Added `grounded registry` to list merged registry types and authored specs,
  with human-friendly grouped output and JSON output for tooling.
- Clarified the metamodel nomenclature so governed top-level kinds are
  described as `registry_type` units and generated views render them as
  `Grounded Types`.
- Kept `spec_type` as a compatibility spelling in older registries and example
  projects while the docs and UI move to the registry_type wording.
- Clarified the `spec` / `registry_type` / `knowledge_unit` hierarchy so the
  docs distinguish authored instances from the governing type definitions and
  the shared base contract.
- Added `registry_unit` as the minimal root concept and demoted
  `knowledge_unit` to the documented human-facing extension so evidence fields
  are no longer treated as part of the root base.
- Made reference and evidence fields opt-in on specific registry types instead
  of implicit behavior inherited from `registry_unit` or `knowledge_unit`.

## 0.12.2 - 2026-05-30

- Removed the non-core `PROJECT-DOMAIN-001` canonical project fact and
  trimmed project-memory prose to match the remaining bootstrap shape.
- Updated the bootstrap seed, generated LLM context, and tests so the
  core-only project-memory flow still renders, validates, audits, and verifies
  cleanly.
- Extracted project-memory loading from `registry.py` into a
  `project_memory` business module with JSON/filesystem infrastructure
  adapters and a `SpecRegistry` compatibility layer.
- Made duplicate IDs, type hierarchy validation, shape validation, reference
  validation, backlinks, and active/retired views independently testable.
- Added guardrails for type hierarchy cycles and pathless units that cannot be
  represented by the filesystem-shaped compatibility registry.

## 0.12.1 - 2026-05-27

- Updated generated documentation tooltips so rich-text Grounded references in
  target descriptions render as clickable links instead of raw bracket syntax.
- Kept hoisted tooltips interactive long enough for readers to move from the
  source link into tooltip links.

## 0.12.0 - 2026-05-27

- Added generated documentation link tooltips. Hovering or focusing a
  `grounded-link` now shows the referenced unit's label, stable ID, type, and
  short description, or tag counts for tag links.

## 0.11.0 - 2026-05-27

- Added typed tags alongside legacy string tags. Knowledge units and field
  definitions can now use tags such as
  `{ "type": "EntityType", "value": "BusinessEntity" }`.
- Added `tag_types` declarations in the type registry so projects can validate
  typed tag vocabularies.
- Added `reference_tag_constraints` for reference fields, allowing a spec type
  to require referenced targets to carry a specific typed tag.
- Added validation guardrails for unknown tag types, unknown tag values,
  malformed tag lists, invalid tag constraints, and reference targets missing
  required typed tags.
- Documented typed tag usage in the README, concepts guide, and CLI reference.

## 0.10.0 - 2026-05-27

- Added CLI project-memory search commands for maintainer and LLM workflows:
  `grounded search`, `grounded entities`, `grounded specs`, `grounded spec`, and
  `grounded check-new`.
- Search results rank exact ID/name matches, aliases, text matches, token
  overlap, and fuzzy name matches, with JSON output for automation.
- Added `specs --uses` to find specs related to a matching entity or spec.
- Documented the search workflow in the README, CLI reference, and LLM workflow
  guide.
- Added Grounded coverage for the search workflow through
  `GROUNDED-DECISION-054` and `GROUNDED-TEST-019`.

## 0.9.0 - 2026-05-27

- Added graph output profiles for `grounded graph`: `docs`, `compact`, and
  `debug`, with `docs` now the default.
- Improved documentation graph output with structured Graphviz HTML labels,
  focus-node highlighting, softer layout styling, kind grouping, edge labels,
  collapsed lifecycle values, and field summary nodes.
- Updated generated docs sidebar navigation so section items are collapsed under
  accordion headings by default, with the active unit section opened on unit
  pages.
- Added content-hash query strings to the generated `grounded-link.js` module URL
  so browsers do not keep stale bundled component behavior after rendering.
- Added generated Todo graph DOT/PNG artifacts for docs, compact, and debug
  graph profiles.

## 0.8.0 - 2026-05-27

- Added a bundled `grounded-theme-toggle` Lit component to generated docs.
- Generated docs now persist explicit light/dark theme choices locally while
  continuing to follow the system color scheme when no preference is set.
- Updated the default generated documentation stylesheet to follow `DESIGN.md`
  tokens for color, typography, spacing, radius, and metadata pills.
- Switched the committed `DESIGN.md` source and rendered docs styling to the
  Notion design brief.
- Added GitHub Pages publishing prep for the standalone Todo demo.

## 0.7.0 - 2026-05-27

- Added `grounded graph SPEC-ID` to emit Graphviz DOT relationship graphs from
  the canonical Grounded registry.
- Graph export traverses outgoing references and backlinks from a starting
  knowledge unit with configurable `--depth`.
- Added `--include-type` and `--exclude-type` filters for graph node kinds, plus
  optional `--output` file writing.

## 0.6.0 - 2026-05-27

- Added reusable bundled Lit components for documentation pages:
  `grounded-doc-header`, `grounded-section`, `grounded-pill-link-list`,
  `grounded-detail-list`, and `grounded-detail-row`.
- Updated unit pages to use `grounded-doc-header` for type badge, title,
  rich lead text, and copy-ID actions.
- Increased the bundled documentation font token scale so generated docs use
  readable `1rem` body text by default.

## 0.5.0 - 2026-05-27

- Added `grounded-compact-list` and `grounded-compact-item` Lit components for
  dense name-and-description rows with optional internal links.
- Render tag member pages with compact item lists instead of full unit cards.
- Documented the compact list components in the generated project feature list.

## 0.4.0 - 2026-05-27

- Added constrained inline rich text for prose fields.
- Added internal link syntax: `[[SPEC-ID]]`, `[[SPEC-ID|label]]`, and
  `[[SPEC-ID#fragment|label]]`.
- Added tag link syntax: `[[tag:name|label]]`.
- Render inline rich text as safe `grounded-link`, `strong`, `em`, and `code`
  markup in generated HTML.
- Treat inline spec links as graph references for validation, backlinks, and
  generated context.
- Keep backtick code spans literal so syntax examples do not validate as real
  links.

## 0.3.0 - 2026-05-27

- Added first-class `slice` knowledge units for scoped documentation views.
- Rendered slice pages at `slices/<slug>/index.html` with scoped navigation,
  search, tag data, metadata, template override, and stylesheet support.
- Changed the default generated docs entry page to `index.html`.
- Required every knowledge unit to include a `description`.
- Added extension-point guidance: projects should extend through registries,
  schemas, templates, styles, slice metadata, and verification specs rather than
  directly editing bundled templates, validation code, or rendering functions.
- Added generated-output cleanup for obsolete slice and legacy entry pages.
