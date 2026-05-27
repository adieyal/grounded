---
last_updated: 2026-05-27
---

# Changelog

All notable Lattice changes are recorded here starting with `0.3.0`.

## 0.9.0 - 2026-05-27

- Added graph output profiles for `lattice graph`: `docs`, `compact`, and
  `debug`, with `docs` now the default.
- Improved documentation graph output with structured Graphviz HTML labels,
  focus-node highlighting, softer layout styling, kind grouping, edge labels,
  collapsed lifecycle values, and field summary nodes.
- Updated generated docs sidebar navigation so section items are collapsed under
  accordion headings by default, with the active unit section opened on unit
  pages.
- Added content-hash query strings to the generated `lattice-link.js` module URL
  so browsers do not keep stale bundled component behavior after rendering.
- Added generated Todo graph DOT/PNG artifacts for docs, compact, and debug
  graph profiles.

## 0.8.0 - 2026-05-27

- Added a bundled `lattice-theme-toggle` Lit component to generated docs.
- Generated docs now persist explicit light/dark theme choices locally while
  continuing to follow the system color scheme when no preference is set.
- Updated the default generated documentation stylesheet to follow `DESIGN.md`
  tokens for color, typography, spacing, radius, and metadata pills.
- Switched the committed `DESIGN.md` source and rendered docs styling to the
  Notion design brief.
- Added GitHub Pages publishing prep for the standalone Todo demo.

## 0.7.0 - 2026-05-27

- Added `lattice graph SPEC-ID` to emit Graphviz DOT relationship graphs from
  the canonical Lattice registry.
- Graph export traverses outgoing references and backlinks from a starting
  knowledge unit with configurable `--depth`.
- Added `--include-type` and `--exclude-type` filters for graph node kinds, plus
  optional `--output` file writing.

## 0.6.0 - 2026-05-27

- Added reusable bundled Lit components for documentation pages:
  `lattice-doc-header`, `lattice-section`, `lattice-pill-link-list`,
  `lattice-detail-list`, and `lattice-detail-row`.
- Updated unit pages to use `lattice-doc-header` for type badge, title,
  rich lead text, and copy-ID actions.
- Increased the bundled documentation font token scale so generated docs use
  readable `1rem` body text by default.

## 0.5.0 - 2026-05-27

- Added `lattice-compact-list` and `lattice-compact-item` Lit components for
  dense name-and-description rows with optional internal links.
- Render tag member pages with compact item lists instead of full unit cards.
- Documented the compact list components in the generated project feature list.

## 0.4.0 - 2026-05-27

- Added constrained inline rich text for prose fields.
- Added internal link syntax: `[[SPEC-ID]]`, `[[SPEC-ID|label]]`, and
  `[[SPEC-ID#fragment|label]]`.
- Added tag link syntax: `[[tag:name|label]]`.
- Render inline rich text as safe `lattice-link`, `strong`, `em`, and `code`
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
