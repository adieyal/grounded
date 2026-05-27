# Todo Lattice Example

This example shows how Lattice keeps a small app's project knowledge in sync.

The Todo domain includes:

- domain terms such as todo items
- lifecycle states such as open, completed, and archived
- rules and invariants about how the domain should behave
- workflow notes that explain how the pieces fit together
- generated documentation built from the same source specs

The point is not todos. The point is that the vocabulary, rules, examples, and generated docs all come from the same canonical project memory.

## Try it

Run the example from the repository root:

```sh
uv run lattice --root examples/todo validate
uv run lattice --root examples/todo render
uv run lattice --root examples/todo audit
```

The generated documentation is written to `examples/todo/site`.

## What to look for

After rendering, open the generated site and look for:

- stable IDs on each project fact
- links between related facts
- backlinks showing what refers to a fact
- generated search data
- docs that can be regenerated instead of edited by hand

This is the adoption pattern for real projects: start with a few important facts, link them together, render the docs, then add deeper checks later.

## Publishing

When this repository is published on GitHub, enable GitHub Pages with the source set to GitHub Actions. The workflow at `../../.github/workflows/todo-pages.yml` renders this example and uploads `examples/todo/site` as the Pages artifact.
