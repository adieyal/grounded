---
last_updated: 2026-05-27
---

# LLM Workflows

Lattice is useful for LLM-assisted development because agents are vulnerable to stale, duplicated, and ambiguous project context.

A normal prompt can tell an agent what to do today. Lattice gives the agent durable project memory it can reference, update, and validate.

## The problem with plain prompt context

Plain prompt context drifts easily:

- old docs remain in the context window
- agents invent names for concepts that already exist
- business rules are copied into multiple prompts
- implementation plans repeat decisions without linking to their owner
- generated summaries become stale but still sound authoritative

The failure mode is not that the agent knows nothing. The failure mode is that it knows several inconsistent versions of the same thing.

## What Lattice gives the agent

Lattice gives the agent:

- stable IDs for important facts
- one owner for each durable rule, term, workflow, or decision
- generated context built from validated specs
- links between related facts
- verification commands for facts that need proof
- a reporting convention: name the Lattice IDs changed

## Basic agent workflow

Before a non-trivial change, the agent should:

1. Read `lattice.yml`.
2. Find relevant existing specs.
3. Update the existing owner if the fact already exists.
4. Create a new spec only when no owner exists.
5. Use the registry before inventing a new kind.
6. Add a `schema_gap` when the current shapes cannot express the fact cleanly.
7. Regenerate docs and context with `lattice render`.
8. Run `lattice validate` and `lattice audit`.
9. Report changed Lattice IDs.

This turns project memory into part of normal implementation work instead of a separate documentation chore.

## Updating AGENTS.md

Use:

```bash
uv run lattice init --update-agents
```

This adds a Lattice section to `AGENTS.md` so coding agents know how to work with project memory.

The important instruction is not “read these docs”. The important instruction is:

> If the change introduces or changes durable project knowledge, update the canonical Lattice owner in the same change.

## Good LLM-facing facts

Good facts for LLM context are facts the agent must not improvise:

- domain terms
- architecture boundaries
- business rules
- lifecycle states
- API contracts
- event names and payloads
- semantic testing expectations
- project-specific workflows
- “do not do this” constraints

Bad facts for LLM context are transient details:

- temporary TODOs
- implementation notes that will be deleted soon
- one-off debugging observations
- guesses that have not become project policy

## Using IDs in prompts and plans

Prefer this:

> Implement the report date formatting change according to `REPORT-RULE-001`. Update the verification if the rule changes.

Avoid this:

> Make sure dates work properly. You know, the UTC thing we discussed before.

Stable IDs reduce ambiguity. They also make reviews sharper because everyone can inspect the same owner.

## Agent reporting

When an agent finishes a change, it should report:

- which Lattice IDs changed
- which generated files were refreshed
- which validation, audit, or verification commands ran
- why no Lattice update was needed, if the change did not affect durable knowledge

Example:

```text
Changed Lattice IDs:
- REPORT-RULE-001
- REPORT-VERIFY-001

Checks run:
- uv run lattice validate
- uv run lattice render --check
- uv run lattice audit
```

## Keep the loop small

Do not ask the agent to model the whole repository.

Ask it to find or create the canonical owner for the specific rule, term, workflow, or decision affected by the current change.

That is where Lattice gives fast value.
