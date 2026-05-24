---
last_updated: 2026-05-24
---

# Link Rendering Guidance

Use `lattice-link` whenever a response or generated page refers to a canonical Lattice unit by ID.

Prefer inline links when the unit is part of the sentence:
- "Track the boundary in `PROJECT-WORKFLOW-001`."
- "This rule is owned by `PROJECT-RULE-003`."
- "The slice is described by `PROJECT-CONCEPT-003`."

Use the short display label when it improves readability, but keep the canonical ID as the target. If the same sentence mentions multiple canonical units, link each one on first mention.

Use links for:
- ownership
- constraints
- workflows
- examples
- gaps
- decisions

Avoid:
- bare IDs when a link would be clearer
- collecting all links into a separate list when the text itself can carry the reference
- linking transient implementation details that are not canonical owners

When the output is HTML or rendered docs, prefer `lattice-link` markup. When the output is plain text, use a direct markdown link to the canonical spec or a concise inline reference if markup is not available.
