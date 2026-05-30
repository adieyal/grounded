---
last_updated: 2026-05-24
---

# Enum Guidance

Use `enum` for a closed set of named values.

Rules:
- An enum should describe a finite vocabulary, not an open-ended list.
- Render the values explicitly on the enum page.
- Use enums when the set is stable enough that callers can reason over the full list.
- Prefer short, readable value names when the values will be shown often.
- Do not model tags as enums; tags are project-defined metadata, not a closed core vocabulary.

Good enum cases:
- lifecycle states
- categories with a fixed allowed set
- type labels that are part of the canonical model

Avoid:
- open-ended labels
- ad hoc grouping values that may change per project
- values that are really tags or display hints
