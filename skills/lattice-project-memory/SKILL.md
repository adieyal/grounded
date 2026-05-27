---
last_updated: 2026-05-27
name: lattice-project-memory
description: Use Lattice as the primary source of truth for specs, durable project knowledge, generated docs, and drift checks.
---

# Lattice Project Memory

## Use This Skill When

- Adding or changing durable project knowledge
- Writing specs, rules, examples, workflows, decisions, or architecture notes
- Defining or changing domain terminology, glossary entries, enum vocabularies, slices, or project-defined tags
- Preparing LLM context from project facts
- Updating tests that prove project rules or examples
- Reviewing drift between docs, code, tests, and specs

## Workflow

1. Read `lattice.yml`.
2. Load the relevant specs under the configured `specs_dir`.
3. Identify the single canonical owner for each idea before editing.
4. Update an existing spec when the fact already has an owner.
5. Create a new spec only when no owner exists.
6. Check `lattice/registry/spec-types.json` before inventing a spec kind.
7. Capture unmet schema needs as `schema_gap` specs.
8. Check `domain_object` specs before naming domain concepts in code or docs.
9. Give every knowledge unit a `description` that explains what it is and what it is used for.
10. Use `short_name` when a durable unit needs a concise display alias in generated views.
11. Model closed value sets as `enum` where the current registry supports it.
12. Model scoped documentation views as `slice` units with explicit `members`, slice metadata, and optional `index_template` or `style_path`.
13. Treat project-defined tags as metadata on knowledge units or field definitions, not as new domain concepts.
14. Use project-owned `verification` specs for checks against code, files, or generated artifacts; do not encode those checks as template overrides.
15. Reference specs by stable ID from tests, code, and non-generated docs.
16. Update Lattice in the same change when work introduces or changes durable knowledge.
17. Regenerate views with `lattice render`.
18. Run `lattice validate` and `lattice audit`.
19. Report changed Lattice IDs, or state that no durable knowledge changed.

## Non-Negotiables

- Do not duplicate durable facts across artifacts.
- Do not leave Lattice stale after changing durable project meaning.
- Do not define domain terms outside glossary/domain-object specs when the meaning is durable.
- Do not invent new spec kinds without updating the type registry and templates.
- Do not hide a schema limitation in prose; create a `schema_gap` owner.
- Do not directly edit bundled Lattice templates, validation code, or rendering functions for project-specific behavior; extend through the type registry, JSON Schemas, project template overrides, styles, slice metadata, or verification specs instead.
- Do not treat `short_name` as canonical identity.
- Do not treat tags as modeled fields or as a substitute for ownership.
- Do not treat field tags as parent-object fields.
- Do not encode code-existence checks in templates when a verification spec is the right owner.
- Do not manually edit files under `lattice/generated`.
- Do not invent a competing term, rule, workflow, or decision if a canonical spec exists.
- Treat broken references, stale generated views, and untested required specs as drift.
- If two artifacts disagree, resolve the source-of-truth ownership first.

## Reporting

When reporting work, include changed Lattice IDs and validation results.
