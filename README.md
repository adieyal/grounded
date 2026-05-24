---
last_updated: 2026-05-24
---

# Lattice

Lattice is executable project memory: strongly typed knowledge units, linked
into a validated project graph.

Every durable project fact should have one canonical owner. Generated docs,
LLM context packs, code references, and tests should point back to that owner
instead of duplicating the idea in prose. Drift is a bug.

## MVP Commands

```bash
lattice init
lattice validate
lattice verify
lattice render --check
lattice audit
```

## Core Ideology

- A fact is authored once.
- Every fact is a typed knowledge unit derived from the core parent shape.
- Other artifacts reference it by stable ID.
- Type-specific JSON Schemas validate unit shape.
- Optional verification units run project-specific commands.
- Human docs and LLM context are generated views.
- Rendering is template-based and overrideable.
- Search is generated from the same registry as links and backlinks.
- Validation detects stale views, broken references, and coverage drift.
- Redundant project knowledge is suspicious until ownership is clear.

## Project Layout

```text
lattice.yml
lattice/
  specs/
  registry/
  schemas/
  templates/
  renderers/
    templates/
  generated/
    docs/
    llm/
```

`lattice init` creates this layout and adds a Lattice section to `AGENTS.md`.
