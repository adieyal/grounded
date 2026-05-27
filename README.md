---
last_updated: 2026-05-27
---

# Lattice

Lattice helps teams keep project knowledge from drifting.

It gives important project facts — rules, decisions, domain terms, workflows, examples, and verification commands — one source of truth. From that source, Lattice can generate human docs, generate LLM context, validate links, run project-specific checks, and detect stale generated views.

Use it when your project has important knowledge scattered across README files, architecture docs, tests, prompts, issue comments, and source code — especially when LLMs are helping write code.

## The problem

Most projects repeat the same idea in many places:

- A business rule in a design doc.
- A slightly different version in a README.
- A test that proves the behaviour.
- An LLM prompt that explains the rule.
- A code comment that uses another name for the same concept.

At first this is fine. Later, one copy changes and the others do not.

Lattice treats that as drift.

## What Lattice gives you

- One canonical owner for each durable project fact.
- Stable IDs that docs, tests, code, prompts, and plans can reference.
- Structured JSON specs so important knowledge has a predictable shape.
- Generated docs for humans.
- Generated context for LLM agents.
- Validation for broken references.
- Verification commands for project-specific checks.
- Audits for stale generated views and coverage drift.

## A tiny example

Imagine your project has this rule:

> Date-only reports must use UTC semantics so the displayed date does not shift by user timezone.

Instead of leaving that rule only in prose, give it a stable Lattice ID:

```json
{
  "id": "REPORT-RULE-001",
  "type": "business_rule",
  "name": "Date-only reports use UTC",
  "owner": "reporting",
  "status": "active",
  "description": "Defines how date-only values are displayed in generated reports.",
  "statement": "Date-only report fields must be formatted using UTC semantics, not local browser timezone semantics.",
  "tests": ["REPORT-VERIFY-001"]
}
```

Now docs, tests, generated LLM context, review comments, and implementation plans can all point to `REPORT-RULE-001` instead of rewriting the rule in five places.

That is the core idea: **important project knowledge gets one home, then everything else links back to it.**

## Quick start

From a checkout:

```bash
uv sync
uv run lattice init
uv run lattice validate
uv run lattice render
```

This creates a Lattice project memory directory, a starter registry, starter schemas, generated docs, and generated LLM context.

Then add one real project fact: a domain term, business rule, architecture decision, workflow, or verification command. Do not start by modelling the whole project.

Run the checks again:

```bash
uv run lattice validate
uv run lattice render --check
uv run lattice audit
```

## Your first useful spec

Good first candidates are facts that already cause confusion or repeated explanations:

- “Revenue means sales excluding tax.”
- “Manual supplier-item aliases outrank fuzzy matches.”
- “Date-only report fields use UTC semantics.”
- “Generated docs must not be edited by hand.”
- “A completed todo cannot be reopened without an explicit reopen action.”

Start with one fact. Give it a stable ID. Link other docs, tests, plans, and prompts back to that ID.

## Common commands

| Command | What it does |
|---|---|
| `lattice init` | Adds Lattice project memory to an existing repo. |
| `lattice validate` | Checks that specs are well-formed and references resolve. |
| `lattice render` | Generates human docs and LLM context from the specs. |
| `lattice render --check` | Fails if generated outputs are stale. |
| `lattice verify` | Runs project-specific verification commands declared in specs. |
| `lattice audit` | Checks for drift and missing coverage. |
| `lattice graph SPEC-ID` | Shows relationships around one project fact as Graphviz DOT. |

During local development, prefer `uv run lattice ...` so the command uses the checkout.

## Adopt incrementally

You do not need to model your whole system on day one.

### Level 1: Canonical glossary

Use Lattice for important project terms.

Good for domain language, renamed concepts, avoiding duplicate terminology, and giving LLMs stable vocabulary.

### Level 2: Rules and decisions

Add business rules, architecture decisions, assumptions, examples, and workflows.

Good for keeping design intent visible and linking implementation plans to stable IDs.

### Level 3: Generated docs and LLM context

Render human docs and LLM-readable context from the same specs.

Good for onboarding, code review, agent workflows, and reducing stale prompt instructions.

### Level 4: Verification and drift checks

Use verification specs and audits to prove that important facts still have checks.

Good for CI, semantic contracts, executable documentation, and project governance.

## When to use Lattice

Use Lattice when:

- project knowledge repeatedly drifts between docs, tests, code, and prompts
- LLM agents need reliable project context
- domain vocabulary matters
- business rules must stay linked to tests or checks
- generated docs should come from validated source material
- you want a small, incremental path toward executable documentation

## When not to use Lattice

Lattice is probably too much if:

- your project has very little durable domain knowledge
- your docs rarely affect implementation
- you only need a normal README
- nobody will run validation, rendering, or audit commands
- you are not ready to decide which artifact owns an important fact

## Examples

- [Todo example](examples/todo/README.md): a small domain showing terms, lifecycle states, rules, links, and generated docs.

## Deeper docs

- [Getting started](docs/getting-started.md)
- [Core concepts](docs/concepts.md)
- [Incremental adoption](docs/incremental-adoption.md)
- [LLM workflows](docs/llm-workflows.md)
- [Drift checks](docs/drift-checks.md)
- [CLI reference](docs/cli-reference.md)
- [Publishing notes](docs/PUBLISHING.md)
- [Changelog](CHANGELOG.md)

## Project layout

```text
lattice.yml
.lattice/
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

`lattice init` creates this layout. Use `lattice init --lattice-dir path/to/memory` to choose a different project directory. Use `lattice init --update-agents` to add a Lattice section to `AGENTS.md`.

## Todo demo publishing

The Todo example lives in `examples/todo`. Its rendered site is ignored by git and is generated by the GitHub Pages workflow in `.github/workflows/todo-pages.yml`.
