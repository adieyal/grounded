from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .audit import audit
from .bootstrap import init_project
from .config import load_config
from .graphviz import graphviz_dot_for
from .registry import load_registry
from .render import render_all
from .verify import verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lattice", description="Executable project memory."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root. Defaults to nearest lattice.yml or cwd.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    init_parser = subcommands.add_parser("init", help="Bootstrap Lattice in a project.")
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite scaffold files when they already exist.",
    )
    init_parser.add_argument(
        "--lattice-dir",
        type=Path,
        default=Path(".lattice"),
        help="Directory for Lattice project files. Defaults to .lattice.",
    )
    init_parser.add_argument(
        "--update-agents",
        action="store_true",
        help="Add or update the Lattice section in AGENTS.md. Defaults to off.",
    )

    subcommands.add_parser("validate", help="Validate specs and references.")

    render_parser = subcommands.add_parser(
        "render", help="Render generated docs and LLM context."
    )
    render_parser.add_argument(
        "--check", action="store_true", help="Fail if generated outputs are stale."
    )

    subcommands.add_parser("audit", help="Run drift and coverage audits.")
    subcommands.add_parser(
        "verify",
        help="Run project-specific verification commands declared by knowledge units.",
    )
    graph_parser = subcommands.add_parser(
        "graph", help="Generate a Graphviz DOT relationship graph."
    )
    graph_parser.add_argument("start", help="Starting knowledge-unit ID.")
    graph_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Relationship depth from the starting ID. Defaults to 1.",
    )
    graph_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write DOT to this file. Defaults to stdout.",
    )
    graph_parser.add_argument(
        "--include-type",
        action="append",
        default=[],
        help="Only include these spec types. May be repeated or comma-separated.",
    )
    graph_parser.add_argument(
        "--exclude-type",
        action="append",
        default=[],
        help="Exclude these spec types. May be repeated or comma-separated.",
    )

    args = parser.parse_args(argv)
    root = (args.root or Path.cwd()).resolve()

    if args.command == "init":
        created = init_project(
            root,
            force=args.force,
            lattice_dir=args.lattice_dir,
            update_agents=args.update_agents,
        )
        for path in created:
            print(f"wrote {path.relative_to(root)}")
        return 0

    config = load_config(root)
    registry = load_registry(config)

    if args.command == "validate":
        return _print_issues(
            config.root, registry.issues, success="Lattice specs are valid."
        )

    if args.command == "render":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        stale = render_all(config, registry, check=args.check)
        if stale:
            for path in stale:
                print(f"stale generated view: {path}", file=sys.stderr)
            return 1
        print(
            "Lattice generated views are current."
            if args.check
            else "Rendered Lattice generated views."
        )
        return 0

    if args.command == "audit":
        issues = [*registry.issues, *audit(config, registry)]
        return _print_issues(config.root, issues, success="Lattice audit passed.")

    if args.command == "verify":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        return _print_issues(
            config.root,
            verify(config, registry),
            success="Lattice verification passed.",
        )

    if args.command == "graph":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        try:
            dot = graphviz_dot_for(
                registry,
                args.start,
                depth=args.depth,
                include_types=_type_filter_set(args.include_type),
                exclude_types=_type_filter_set(args.exclude_type),
            )
        except KeyError:
            print(f"unknown starting knowledge-unit ID: {args.start}", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if args.output is None:
            print(dot, end="")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(dot, encoding="utf-8")
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


def _type_filter_set(values: list[str]) -> set[str] | None:
    result = {
        item.strip() for value in values for item in value.split(",") if item.strip()
    }
    return result or None


def _print_issues(
    root: Path, issues: list[object], *, success: str | None = None
) -> int:
    errors = 0
    for issue in issues:
        severity = getattr(issue, "severity", "error")
        print(issue.format(root), file=sys.stderr)
        if severity == "error":
            errors += 1
    if errors:
        return 1
    if success:
        print(success)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
