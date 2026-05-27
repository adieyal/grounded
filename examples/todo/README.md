# Todo Lattice Example

This example defines a todo domain as typed, linked Lattice knowledge units. It
contains only the model: business entities, lifecycle vocabulary, data types,
invariants, and a workflow. It does not include implementation code.

Render it from the repository root with:

```sh
uv run lattice --root examples/todo render
```

The generated documentation is written to `examples/todo/site`.

When this repository is published on GitHub, enable GitHub Pages with the
source set to GitHub Actions. The workflow at
`../../.github/workflows/todo-pages.yml` renders this example and uploads
`examples/todo/site` as the Pages artifact.
