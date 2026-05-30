---
last_updated: 2026-05-30
---

# Agent Instructions

<!-- grounded:start -->
## Grounded Project Memory

Grounded is the primary source of truth for durable project specs, decisions,
rules, workflows, examples, and LLM-readable context. Grounded registry units
are strongly typed, schema-validated nodes.

The agent is responsible for using, creating, and maintaining this knowledge
base as part of normal project work. Do not treat Grounded as optional
documentation after the fact.

Before implementing or documenting a non-trivial change:

1. Check `grounded.yml` for the configured registry.
2. Search existing Grounded specs for the owner of the idea.
3. Update the existing canonical fact instead of duplicating it.
4. Create a new fact only when no existing owner exists.
5. Use the type registry before inventing a new registry type.
6. If the current schema cannot express the fact cleanly, create a `schema_gap`
   instead of smuggling meaning into prose.
7. Reference facts by stable ID from tests, code, docs, and plans.
8. Use domain_object units for durable domain nouns instead of inventing synonyms.
9. Give every documented unit a `description` that explains what it is and what
   it is used for.
10. If the change introduces or changes a durable rule, workflow, decision,
   domain object, example, invariant, or assumption, update Grounded in the same
   change.
11. Do not directly edit bundled Grounded templates, validation code, or
   rendering functions for project-specific behavior. Extend through the type
   registry, JSON Schemas, project template overrides, styles, slice metadata,
   or verification specs instead.
12. Regenerate generated views with `grounded render`.
13. Do not manually edit generated Grounded documentation.
14. Run `grounded validate`, `grounded verify`, and `grounded audit`.
15. Report the Grounded IDs changed or explain why no canonical fact changed.

Every idea, fact, rule, workflow, decision, and durable assumption should have
one owner. If another artifact conflicts with a Grounded spec, treat that as
drift and resolve the ownership conflict.
<!-- grounded:end -->
