---
last_updated: 2026-05-30
---

# Theory of Lattice

This document explains the intent behind Lattice. The canonical project-memory
facts live in `lattice/specs`; this overview is grounded in
`LATTICE-THEORY-001`, `PROJECT-CONCEPT-001`, and `PROJECT-RULE-001`.

## What Lattice Is

Lattice is executable project memory.

It is a lightweight, machine-readable layer for durable project knowledge:
business rules, architectural boundaries, workflows, examples, verification
expectations, decisions, and other facts that should not live only in scattered
prose or implicit code structure.

The core idea is simple: every durable fact should have one canonical owner.
Other artifacts can reference that owner, but should not duplicate or
reinterpret it. When code, tests, docs, plans, and LLM context all carry
slightly different versions of the same idea, the project develops semantic
drift. Lattice treats that drift as something to detect and repair.

Lattice is not a runtime framework, business rule engine, or replacement for
implementation. Code remains the thing that runs. Tests remain the proof that
behavior works. Lattice provides the declared intent and coordination surface
around them.

While the philosophy is broader than any file format, the canonical practical
implementation is schema-driven. JSON schemas precisely define each unit of
knowledge, and references between those units form a graph of project meaning.
That graph is what lets Lattice validate not only document shape, but also
relationships between concepts, rules, examples, tests, and other artifacts.
Within that metamodel, governed top-level kinds are registry types, nested
shapes are value types, and generated docs are downstream views rather than the
authoritative source.

The clean relationship is:

- `registry_type` defines the kind.
- `registry_unit` defines the minimal base shape.
- `knowledge_unit` is the documented human-facing extension.
- `spec` is an authored instance.

## Why It Exists

Older documentation-heavy approaches tried to preserve project knowledge in long
documents, but those documents often became stale, expensive to maintain, and
disconnected from delivery. Agile practice corrected part of that failure by
making code and tests more central, but it also pushed many important semantics
into implicit form.

That implicitness becomes more costly in LLM-assisted development. LLMs infer
intent from context. If the context is fragmented or stale, they can introduce
duplicate concepts, inconsistent terminology, architectural violations, or
parallel abstractions that look plausible but do not belong to the project.

Lattice exists to reduce that coordination cost. It gives humans and LLMs a
compact, auditable source of project truth, then lets tooling validate references,
coverage, generated context, and drift.

## Core Model

Lattice separates four concerns that are often blurred together:

- Code is operational truth.
- Tests are behavioral proof.
- Canonical specs are semantic intent and ownership.
- Generated docs and context packs are views over the canonical registry.

The core metamodel is intentionally smaller than most project vocabularies. A
repo can define its own domain terms on top of Lattice, but the kernel should
stay focused on registry units, registry types, value types, references, and
generated views.

Put another way: a spec is an authored file or unit; its registry type defines
what it may contain; `registry_unit` supplies only identity, type, lifecycle,
and optional owner/summary metadata; and `knowledge_unit` adds the prose fields
used by human-facing types.

This boundary matters. A Lattice spec can say that a business rule exists, name
the surfaces it affects, link examples, and require verification. It should not
become the implementation of that rule. The useful pressure is coordination, not
turning project docs into a hidden execution engine.

## What It Should Capture

Lattice should focus on durable semantics whose drift is expensive:

- business rules and invariants
- architectural boundaries
- ownership of important concepts
- workflow contracts
- examples and counterexamples that clarify intent
- verification mappings between specs and tests
- decisions or assumptions that future work must preserve
- LLM-readable context that should be stable across sessions

It should not try to model every fact in a project. The system is strongest when
it captures high-value knowledge that is repeatedly misunderstood, crosses module
boundaries, affects correctness, or guides future changes.

## Goals

The goals of Lattice are:

- Give durable facts stable IDs and single ownership.
- Make project knowledge readable by humans and machines.
- Generate human docs and LLM context from the same canonical registry.
- Detect broken references, stale generated views, missing proof, and duplicate
  ownership.
- Tie semantic rules and examples to tests without replacing test code.
- Provide a practical audit surface for CI, pre-commit hooks, and review.
- Support extensible profiles and checks without baking one architecture into
  the core.

The long-term aim is not more documentation. It is less semantic ambiguity.

## Design Philosophy

Lattice should stay boring in implementation and ambitious in effect.

The core should know about schemas, IDs, lifecycle state, checks, reports, and
generated views. Documentation and evidence fields should be opt-in type
features rather than universal root fields. More opinionated ideas, such as
business-module schemas or import-boundary linting, should live as profiles or
integrations. That keeps the base system useful across projects without forcing
every project into one architectural style.

Checks should also be honest about what they prove. Deterministic validation can
prove that a referenced ID exists, a required field is present, or a generated
view is stale. It cannot prove that a team has perfectly separated business
logic. Lattice should distinguish proven facts, partial checks, advisory findings,
and human judgment.

Wherever a semantic claim can be checked deterministically, Lattice should check
it deterministically. Shape validation is the floor, not the ceiling. The system
should also validate reference semantics, ownership, coverage, stale generated
views, and other mechanically knowable signals that help prevent drift and
split-brain project knowledge.

## Relationship to LLMs

Lattice is especially useful in LLM-era development because LLMs need durable,
bounded context. A context pack generated from canonical specs can tell an agent
which concepts exist, which rules are active, which IDs are valid, and where
semantic ownership lives.

That acts as a context firewall. Instead of asking an LLM to infer project
memory from scattered files, the project can provide a curated registry of what
must be preserved. The goal is not to make LLMs unquestionable. It is to make
their work easier to audit and less likely to invent a second version of the
project.

## Non-Goals

Lattice should avoid becoming:

- a runtime business rule engine
- a universal specification language
- a code-generation-first platform
- a project management system
- a replacement for tests
- a replacement for architectural judgment

Those boundaries are important. If Lattice tries to execute the project, manage
all work, or encode every nuance as custom policy logic, it will recreate the
kind of heavyweight process it is meant to avoid.

## The Short Version

Lattice is a small system for keeping project meaning stable.

It gives durable facts one owner, makes those facts machine-readable, renders
useful views from them, and audits whether the rest of the project still points
back to the same truth.
