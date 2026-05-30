---
last_updated: 2026-05-27
---

# Template Override Notes

Use the default template for most units and conversations. Do not directly edit
bundled Grounded templates, validation code, or rendering functions for
project-specific behavior.

Override pages only when the default flow does not answer a specific question cleanly:
- scope boundary needs its own language
- type choice needs stricter heuristics
- interlinking needs explicit rules
- existing-codebase modeling needs special grounding in observed evidence
- a slice needs its own index page structure or stylesheet

The override pages should sharpen the default flow, not replace it with a competing process.

Use the extension points in this order:
- type registry entries and JSON Schemas for spec shape
- project templates under the configured `renderers/templates` directory
- template inheritance from reusable bundled templates such as `unit-core.html.j2`
  and `slice-index.html.j2`
- slice-level `index_template` and `style_path` for scoped pages
- configured styles and design tokens for presentation
- `verification` specs for project-specific checks
