---
last_updated: 2026-05-27
---

# CLI Reference

The Lattice CLI is intentionally small. Most projects use the same handful of commands.

During local development, run commands through `uv` from the checkout:

```bash
uv run lattice <command>
```

If the package is installed as a console script, `lattice <command>` works directly.

## `lattice init`

Bootstrap Lattice in a project.

```bash
uv run lattice init
```

Useful options:

```bash
uv run lattice init --lattice-dir docs/lattice
uv run lattice init --update-agents
uv run lattice init --force
```

Use `--lattice-dir` when you do not want the default `.lattice` directory.

Use `--update-agents` to add Lattice workflow guidance to `AGENTS.md`.

Use `--force` only when you intentionally want to overwrite scaffold files.

## `lattice validate`

Validate specs and references.

```bash
uv run lattice validate
```

Use this after editing specs or the type registry.

Validation is the first line of defence against broken links and malformed project memory.

## `lattice render`

Render generated docs and LLM context.

```bash
uv run lattice render
```

Use this after changing specs.

Generated output should be treated as a view. Do not edit it by hand.

## `lattice render --check`

Fail if generated outputs are stale.

```bash
uv run lattice render --check
```

Use this in CI or before merging documentation/spec changes.

## `lattice audit`

Run drift and coverage audits.

```bash
uv run lattice audit
```

Use this to catch project-memory problems beyond basic schema validity.

## `lattice verify`

Run project-specific verification commands declared by Lattice specs.

```bash
uv run lattice verify
```

Use this when specs include executable checks for important facts.

Verification is how Lattice moves from structured documentation to executable project memory.

## `lattice graph`

Generate a Graphviz DOT relationship graph around one project fact.

```bash
uv run lattice graph SPEC-ID
```

Useful options:

```bash
uv run lattice graph SPEC-ID --depth 2
uv run lattice graph SPEC-ID --include-type domain_object
uv run lattice graph SPEC-ID --exclude-type schema_gap
uv run lattice graph SPEC-ID --output graph.dot
```

Use this when you want to see what refers to a fact and what the fact depends on.

## `--root`

Most commands accept a project root:

```bash
uv run lattice --root examples/todo validate
uv run lattice --root examples/todo render
uv run lattice --root examples/todo audit
```

Use this for examples, monorepos, or any project where the current working directory is not the Lattice root.

## Common local loop

```bash
uv run lattice validate
uv run lattice render
uv run lattice audit
```

## Common CI loop

```bash
uv run lattice validate
uv run lattice render --check
uv run lattice audit
```

Add `uv run lattice verify` when verification specs are stable enough for CI.
