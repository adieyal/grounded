---
last_updated: 2026-05-27
---

# Core Concepts

Lattice is deliberately small. It is a way to store important project knowledge as checked, linked facts instead of scattered prose.

## Project fact

A project fact is a durable idea that other work depends on.

Examples:

- a domain term
- a business rule
- an architecture decision
- a workflow
- an invariant
- a verification command
- an example that explains a rule

A project fact deserves a stable home when changing it would affect docs, tests, implementation, or LLM context.

## Canonical owner

A canonical owner is the one place where a fact is defined.

Other artifacts may repeat, summarize, or apply the fact, but they should point back to the owner instead of becoming competing sources of truth.

This is the core Lattice rule: **a durable fact is authored once.**

## Knowledge unit

A knowledge unit is the JSON object that owns a project fact.

Every unit has a few common fields:

- `id`: the stable identifier other artifacts can reference
- `name`: the human-readable label
- `owner`: the project area responsible for the fact
- `status`: usually `active`, `draft`, or `retired`
- `description`: what the fact is and what it is used for

Different projects can define richer unit types in their registry.

## Stable IDs

Stable IDs let docs, tests, plans, generated context, and code comments point to the same fact.

A stable ID is useful because people and agents can say:

> This change updates `REPORT-RULE-001`.

That is much better than repeating a paragraph and hoping every copy stays aligned.

## Links and backlinks

Lattice specs can reference other specs.

Those references become links in generated docs and backlinks on the target pages. This makes it easier to answer questions like:

- What tests prove this rule?
- What examples explain this decision?
- What workflows depend on this term?
- What generated context mentions this fact?

## Generated docs

Generated docs are human-readable views built from the specs.

They are not the source of truth. The specs are.

When generated docs are stale, update the specs and render again.

## LLM context

Lattice can generate context for coding agents and other LLM workflows.

The point is not to create more prompt prose. The point is to give agents checked, stable project memory with IDs they can reference when they make changes.

## Verification

A verification spec connects a project fact to a command that can check it.

Examples:

- a pytest command proving a business rule
- a schema validation command
- a frontend contract test
- a documentation audit

This is how project memory becomes executable rather than passive.

## Drift

Drift happens when artifacts that should agree no longer agree.

Examples:

- a generated doc is stale
- a test references a retired rule
- a prompt says one thing and the source spec says another
- a domain term has two competing definitions
- an important fact has no check even though project policy requires one

Lattice does not remove the need for judgement. It gives the project a place to decide ownership, link related facts, and run checks.

## Type registry

The type registry defines the kinds of facts a project can store.

Start with the built-in kinds. Add project-specific kinds only when a repeated shape becomes stable.

Do not invent a new kind just because one fact feels slightly different. That turns the registry into noise.

## Schema gaps

A schema gap records a limitation in the current modelling language.

Use a schema gap when a real project fact does not fit the current registry cleanly.

That is better than hiding structure inside prose or changing core renderer code for one project-specific need.
