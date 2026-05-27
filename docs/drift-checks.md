---
last_updated: 2026-05-27
---

# Drift Checks

Drift is when project artifacts that should agree no longer agree.

Lattice does not pretend all drift can be detected automatically. It gives you a structured place to define important facts, link related artifacts, generate views, and run checks where checks are worth the cost.

## Common drift patterns

### Stale generated docs

The specs changed, but the generated docs or LLM context were not refreshed.

Use:

```bash
uv run lattice render --check
```

This should fail when generated output is stale.

### Broken references

A spec points to an ID that does not exist, was renamed, or was retired without updating dependants.

Use:

```bash
uv run lattice validate
```

Validation keeps links from silently rotting.

### Missing proof

A rule says something important, but there is no verification command proving it.

Use verification specs for facts that need executable evidence.

Then run:

```bash
uv run lattice verify
```

### Competing definitions

Two docs define the same concept differently.

This is partly a human judgement problem. Lattice helps by making ownership explicit: one fact should have one canonical owner, and other artifacts should link back to it.

### LLM context rot

An agent reads old or duplicated instructions and implements against the wrong version of the project.

Use generated LLM context from Lattice specs, and ask agents to report which Lattice IDs they changed.

## The check stack

Use the smallest check that protects the fact.

| Check | Use it for |
|---|---|
| `lattice validate` | Spec shape and broken references. |
| `lattice render --check` | Stale generated docs or LLM context. |
| `lattice audit` | Drift and coverage checks. |
| `lattice verify` | Project-specific executable checks declared by specs. |
| Tests | Code behaviour that proves a rule or contract. |

## What belongs in verification

Verification specs should point to commands that prove important facts.

Good examples:

```text
uv run pytest tests/reports/test_date_only_utc.py
uv run python scripts/validate_specs.py
npm test -- search-input.contract.test.ts
```

Bad examples:

```text
# vague manual instruction
Check that the docs look okay.

# too broad for one fact
uv run pytest
```

A verification command can be broad when the fact is broad, but most facts should have focused checks.

## CI adoption

A minimal CI path is:

```bash
uv run lattice validate
uv run lattice render --check
uv run lattice audit
```

Add `lattice verify` once verification specs are stable and the commands are cheap enough for CI.

## Review adoption

In code review, ask:

- Did this change alter durable project knowledge?
- If yes, which Lattice ID owns that knowledge?
- Did generated docs or context need to be refreshed?
- Are any tests or verification specs now stale?
- Did the author report changed Lattice IDs?

This is the practical value: drift becomes reviewable instead of invisible.
