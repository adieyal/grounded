---
last_updated: 2026-05-27
---

# Incremental Adoption

Lattice works best when adoption starts small.

The mistake is trying to model the whole project. That creates documentation theatre. The useful move is to capture the few facts that already cause drift.

## Level 1: Canonical glossary

Start with terms.

Use Lattice when a project has concepts people keep renaming, redefining, or explaining differently.

Examples:

- “revenue” vs “sales” vs “sales excluding tax”
- “supplier item” vs “ingredient” vs “catalog item”
- “active subject” vs “research subject”
- “semantic contract” vs “unit test”

Value gained:

- stable vocabulary
- easier onboarding
- less LLM invention
- fewer duplicated explanations

Good output after this level:

- a small glossary
- stable IDs for key terms
- generated docs that show definitions and backlinks

## Level 2: Rules and decisions

Next, capture rules and decisions that implementation must respect.

Examples:

- “Date-only report fields use UTC semantics.”
- “Manual supplier-item aliases outrank fuzzy matches.”
- “Generated docs are never edited by hand.”
- “A completed todo cannot be reopened without an explicit reopen action.”

Value gained:

- implementation plans can reference stable IDs
- code reviews can discuss one named rule
- docs and prompts stop competing with each other

Good output after this level:

- 5-20 important rules or decisions
- references from plans, tests, docs, or prompts
- generated docs that make related facts navigable

## Level 3: Generated docs and LLM context

Once the specs are useful, generate views from them.

Use generated docs for humans. Use generated context for LLM agents.

Value gained:

- agents get current project memory
- humans get browsable docs
- generated output can be checked instead of trusted by habit

Good output after this level:

- generated docs in a predictable location
- generated LLM context used by agents or coding workflows
- `lattice render --check` in CI or local review

## Level 4: Verification and drift checks

Only add heavier checks where they are worth it.

A verification spec should answer:

> What executable command proves this fact still holds?

Examples:

- a pytest command for a semantic rule
- a schema validator for spec structure
- a frontend contract test for a UI event contract
- a docs audit for generated output freshness

Value gained:

- important facts have executable proof
- CI can catch drift earlier
- review becomes less dependent on memory

Good output after this level:

- verification specs for the highest-risk facts
- `lattice verify` used locally or in CI
- audits that fail when expected coverage disappears

## Adoption smell checks

You are probably overdoing it if:

- every tiny implementation detail becomes a spec
- people spend more time modelling than shipping
- there are many kinds with only one instance each
- specs contain prose that nobody links to
- generated docs are produced but never read or checked

You are probably underusing it if:

- the same rule keeps being explained in plans and reviews
- agents repeatedly invent nearby but wrong concepts
- tests prove behaviours without naming the rule they protect
- important decisions live only in old PR comments
- generated docs are stale and nobody notices

## Practical rule

Add a Lattice spec when the fact is durable enough that future work should find it, reference it, or prove it.

Everything else can stay normal documentation.
