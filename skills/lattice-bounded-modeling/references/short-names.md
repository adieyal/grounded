---
last_updated: 2026-05-24
---

# Short Name Guidance

Use `short_name` when a knowledge unit needs a concise display label.

Rules:
- `name` stays the canonical unit name.
- `short_name` is optional.
- Use `short_name` for links, backlinks, navigation, search titles, and other dense UI surfaces when the canonical name is too long.
- Do not use `short_name` as a replacement for the canonical identity of the unit.
- Do not show `short_name` in field tables as if it were a modeled domain field.

Good uses:
- `AnalysisReportSectionBlock` with `short_name` of `SectionBlock`
- long concept names that need a compact label in navigation
- link labels that would otherwise be too verbose to scan quickly

When to skip it:
- the canonical name is already short and clear
- the abbreviated label would be ambiguous
- the shortened form would hide important meaning

Modeling approach:
- choose the canonical name for durable meaning
- use `short_name` only as a display alias
- keep prose and rendered links readable, but preserve the full canonical name in source-of-truth metadata
