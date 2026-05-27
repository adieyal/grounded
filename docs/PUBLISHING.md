---
last_updated: 2026-05-27
---

# Publishing

Before publishing Lattice on GitHub:

- Choose and add a `LICENSE` file.
- Add a short repository description and useful repository topics.
- Keep rendered Lattice sites out of git; generate them in CI.
- Enable GitHub Pages with source set to GitHub Actions.
- Confirm the Todo demo workflow succeeds after the first push.
- Add package metadata before package-index publishing: license, classifiers,
  project URLs, and keywords.
- Decide whether to add a general CI workflow for tests, Lattice validation,
  verification, audit, and render checks.

## Todo Demo Pages

The Todo demo is published by `.github/workflows/todo-pages.yml`. The workflow
renders `examples/todo` into `examples/todo/site`, validates and audits the
example project, checks that rendered output is current, and deploys the site as
a GitHub Pages artifact.

The rendered `examples/todo/site` directory stays ignored by git.
