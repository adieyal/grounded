---
last_updated: 2026-05-23
name: lattice-project-memory
description: Use Lattice as the primary source of truth for specs, durable project knowledge, generated docs, and drift checks.
---

# Lattice Project Memory

## Use This Skill When

- Adding or changing durable project knowledge
- Writing specs, rules, examples, workflows, decisions, or architecture notes
- Defining or changing domain terminology and glossary entries
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
9. Reference specs by stable ID from tests, code, and non-generated docs.
10. Update Lattice in the same change when work introduces or changes durable knowledge.
11. Regenerate views with `lattice render`.
12. Run `lattice validate` and `lattice audit`.
13. Report changed Lattice IDs, or state that no durable knowledge changed.

## Non-Negotiables

- Do not duplicate durable facts across artifacts.
- Do not leave Lattice stale after changing durable project meaning.
- Do not define domain terms outside glossary/domain-object specs when the meaning is durable.
- Do not invent new spec kinds without updating the type registry and templates.
- Do not hide a schema limitation in prose; create a `schema_gap` owner.
- Do not manually edit files under `lattice/generated`.
- Do not invent a competing term, rule, workflow, or decision if a canonical spec exists.
- Treat broken references, stale generated views, and untested required specs as drift.
- If two artifacts disagree, resolve the source-of-truth ownership first.

## Reporting

When reporting work, include changed Lattice IDs and validation results.
