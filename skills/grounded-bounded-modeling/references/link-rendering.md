---
last_updated: 2026-05-27
---

# Link Rendering Guidance

Use `grounded-link` whenever a response or generated page refers to a canonical Grounded unit by ID.

Inside Grounded prose fields such as `description`, `summary`, `decision`,
`definition`, `gap`, `suggested_improvement`, and field descriptions, prefer
constrained inline rich text:
- `[[SPEC-ID]]` links to the target using its display name
- `[[SPEC-ID|label]]` links to the target using a custom label
- `[[SPEC-ID#fragment|label]]` links to a target fragment
- `[[tag:name|label]]` links to a project-defined tag

Inline spec links participate in validation, graph references, and backlinks.
Use explicit `references` for durable structural relationships and inline links
for prose-local context.

When the target is a field, member, or sub-section, use the `fragment` attribute so the link points to the exact anchor.
When the display label should differ from the canonical unit name, use the optional `label` attribute.
When linking a project-defined tag, use `type="tag"` so the tag index resolves to the generated tag page.
Use tag links for project-defined labels such as `deprecated` or `planned`, and use field-tag chips only on the field row they annotate.

Prefer inline links when the unit is part of the sentence:
- "Track the boundary in `PROJECT-WORKFLOW-001`."
- "This rule is owned by `PROJECT-RULE-003`."
- "The slice is described by `PROJECT-CONCEPT-003`."
- "Deprecated items are grouped under the `deprecated` tag."

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

When the output is HTML or rendered docs, prefer `grounded-link` markup. When the output is plain text, use a direct markdown link to the canonical spec or a concise inline reference if markup is not available.
