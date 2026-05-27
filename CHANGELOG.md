---
last_updated: 2026-05-27
---

# Changelog

All notable Lattice changes are recorded here starting with `0.3.0`.

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
