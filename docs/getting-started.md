---
last_updated: 2026-05-27
---

# Getting Started

This guide gets you from an ordinary repository to useful Lattice output with the smallest possible commitment.

The goal is not to model the whole project. The goal is to capture one durable project fact, give it a stable ID, and generate checked docs from it.

## 1. Install from a checkout

From the repository root:

```bash
uv sync
uv run lattice --help
```

During local development, prefer `uv run lattice ...` so the command uses the checkout rather than another installed version.

## 2. Add Lattice to a project

```bash
uv run lattice init
```

This writes the starter layout:

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

You can choose a different memory directory:

```bash
uv run lattice init --lattice-dir docs/lattice
```

You can also add Lattice guidance to `AGENTS.md`:

```bash
uv run lattice init --update-agents
```

## 3. Validate the starter project

```bash
uv run lattice validate
```

Validation checks that specs have the expected shape and that links point to real Lattice IDs.

## 4. Render generated docs

```bash
uv run lattice render
```

This generates human-readable docs and LLM-readable context from the same specs.

Do not edit generated files by hand. Edit the source specs, then render again.

## 5. Add one real fact

Start with one fact that already matters.

Good first choices:

- a domain term people use inconsistently
- a rule people keep restating in docs and prompts
- an architecture decision that implementation plans must follow
- a workflow an agent should know before changing code
- a verification command that proves an important contract

Do not start by describing the whole system. One valuable fact is enough.

## 6. Re-run the checks

```bash
uv run lattice validate
uv run lattice render --check
uv run lattice audit
```

Use `render --check` in CI when you want stale generated docs to fail the build.

## 7. Add verification later

Once a fact matters enough to prove, add a `verification` spec that points to the relevant command.

Example uses:

- run a focused pytest file
- run a schema validator
- run a frontend contract test
- run a documentation drift check

Then:

```bash
uv run lattice verify
```

## What good first adoption looks like

A healthy first adoption usually has:

- 3-10 important terms or rules
- generated docs committed or produced in CI, depending on project policy
- one or two verification specs for high-value checks
- Lattice IDs referenced from plans, tests, prompts, or review notes

That is enough to get value without turning the project into a modelling exercise.
