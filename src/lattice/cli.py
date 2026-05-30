from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import audit
from .bootstrap import init_project
from .config import load_config
from .graphviz import graphviz_dot_for
from .registry import load_registry
from .render import render_all
from .search import (
    ENTITY_KINDS,
    build_search_records,
    check_new_payload,
    filter_records,
    print_records,
    print_search_results,
    records_json,
    results_json,
    search_records,
)
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
        help="Run project-specific verification commands declared by specs.",
    )
    graph_parser = subcommands.add_parser(
        "graph", help="Generate a Graphviz DOT relationship graph."
    )
    graph_parser.add_argument("start", help="Starting spec ID.")
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
    graph_parser.add_argument(
        "--profile",
        choices=("docs", "compact", "debug"),
        default="docs",
        help="Graph output profile. Defaults to docs.",
    )
    search_parser = subcommands.add_parser(
        "search", help="Search specs, entities, concepts, and relationships."
    )
    search_parser.add_argument("query", help="Search query.")
    search_parser.add_argument(
        "--kind",
        default="all",
        help="Restrict to a kind, or use entities/specs/all. Defaults to all.",
    )
    search_parser.add_argument("--limit", type=int, default=8)
    search_parser.add_argument("--json", action="store_true")

    entities_parser = subcommands.add_parser(
        "entities", help="List entity-like specs."
    )
    entities_parser.add_argument("--json", action="store_true")
    entities_parser.add_argument("--verbose", action="store_true")

    specs_parser = subcommands.add_parser("specs", help="List available specs.")
    specs_parser.add_argument("--kind", default="all", help="Restrict to one spec kind.")
    specs_parser.add_argument(
        "--uses",
        help="Only show specs that reference the matching entity or spec.",
    )
    specs_parser.add_argument("--limit", type=int, default=None)
    specs_parser.add_argument("--json", action="store_true")
    specs_parser.add_argument("--verbose", action="store_true")

    registry_parser = subcommands.add_parser(
        "registry", help="List registry types and authored specs."
    )
    registry_parser.add_argument("--json", action="store_true")

    spec_parser = subcommands.add_parser("spec", help="Search spec records.")
    spec_parser.add_argument("query", help="Spec search query.")
    spec_parser.add_argument("--limit", type=int, default=5)
    spec_parser.add_argument("--json", action="store_true")

    check_new_parser = subcommands.add_parser(
        "check-new",
        help="Check whether a proposed entity or concept probably already exists.",
    )
    check_new_parser.add_argument("name", help="Proposed entity or concept name.")
    check_new_parser.add_argument("--limit", type=int, default=5)
    check_new_parser.add_argument("--json", action="store_true")

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
                profile=args.profile,
            )
        except KeyError:
            print(f"unknown starting spec ID: {args.start}", file=sys.stderr)
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

    if args.command == "search":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        records = build_search_records(registry)
        results = search_records(records, args.query, kind=args.kind, limit=args.limit)
        if args.json:
            print(results_json(results))
            return 0
        return print_search_results(results)

    if args.command == "entities":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        records = filter_records(build_search_records(registry), "entities")
        if args.json:
            print(records_json(records))
            return 0
        return print_records(records, verbose=args.verbose)

    if args.command == "specs":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        records = filter_records(build_search_records(registry), args.kind)
        if args.uses:
            matches = search_records(records, args.uses, kind="entities", limit=10)
            if not matches:
                matches = search_records(records, args.uses, kind="all", limit=10)
            target_ids = {result.record.id for result in matches if result.score >= 75}
            records = [
                record
                for record in records
                if record.id not in target_ids
                and (
                    any(reference in target_ids for reference in record.references)
                    or any(used_by in target_ids for used_by in record.used_by)
                )
            ]
        if args.limit is not None:
            records = records[: args.limit]
        if args.json:
            print(records_json(records))
            return 0
        return print_records(records, verbose=args.verbose)

    if args.command == "registry":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        if args.json:
            print(json.dumps(_registry_payload(config.root, registry), indent=2))
            return 0
        return _print_registry(config.root, registry)

    if args.command == "spec":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        records = build_search_records(registry)
        results = [
            result
            for result in search_records(records, args.query, kind="specs", limit=args.limit)
            if result.record.kind not in ENTITY_KINDS
        ]
        if args.json:
            print(results_json(results))
            return 0
        return print_search_results(results)

    if args.command == "check-new":
        if registry.issues:
            return _print_issues(config.root, registry.issues)
        payload = check_new_payload(build_search_records(registry), args.name, limit=args.limit)
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        print(f"Query: {payload['query']}")
        print(f"Recommendation: {payload['recommendation']}")
        print()
        print("Closest entities:")
        entity_matches = payload["entity_matches"]
        if entity_matches:
            for result in entity_matches:
                print(f"- {result['name']} ({result['score']}) [{result['id']}]")
                print(f"  {result['reason']}; {result['path']}")
        else:
            print("- none")
        print()
        print("Relevant specs:")
        spec_matches = payload["spec_matches"]
        if spec_matches:
            for result in spec_matches:
                print(f"- {result['name']} ({result['score']}) [{result['id']}]")
                print(f"  {result['description'] or result['reason']}")
        else:
            print("- none")
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


def _registry_payload(root: Path, registry: object) -> dict[str, object]:
    return {
        "registry_types": [
            _registry_type_payload(type_name, type_def)
            for type_name, type_def in sorted(registry.type_defs.items())
        ],
        "specs": [
            _spec_payload(root, spec)
            for spec in sorted(registry.specs, key=lambda item: (item.kind, item.id))
        ],
    }


def _registry_type_payload(type_name: str, type_def: object) -> dict[str, object]:
    return {
        "type": type_name,
        "extends": getattr(type_def, "extends", None),
        "renderer": getattr(type_def, "renderer", None),
        "required": list(getattr(type_def, "required", ())),
        "reference_fields": list(getattr(type_def, "reference_fields", ())),
        "single_reference_fields": list(
            getattr(type_def, "single_reference_fields", ())
        ),
        "nested_reference_fields": [
            ".".join(path)
            for path in getattr(type_def, "nested_reference_fields", ())
        ],
        "verification_fields": list(getattr(type_def, "verification_fields", ())),
        "search_fields": list(getattr(type_def, "search_fields", ())),
    }


def _spec_payload(root: Path, spec: object) -> dict[str, object]:
    path = getattr(spec, "path", None)
    return {
        "id": spec.id,
        "type": spec.kind,
        "name": spec.display_name,
        "owner": spec.owner,
        "status": spec.status,
        "path": path.relative_to(root).as_posix()
        if isinstance(path, Path) and path.is_relative_to(root)
        else str(path),
    }


def _print_registry(root: Path, registry: object) -> int:
    payload = _registry_payload(root, registry)
    registry_types = payload["registry_types"]
    specs = payload["specs"]
    specs_by_type: dict[str, list[dict[str, object]]] = {}
    for spec in specs:
        specs_by_type.setdefault(str(spec["type"]), []).append(spec)

    print("Lattice registry")
    print(
        f"{len(registry_types)} registry types, "
        f"{len(specs)} authored specs"
    )
    print()
    print("Registry types")
    for item in registry_types:
        spec_count = len(specs_by_type.get(str(item["type"]), []))
        extends = item["extends"] or "root"
        print(f"- {item['type']}")
        print(f"  specs: {spec_count}")
        print(f"  extends: {extends}")
        required = item["required"]
        if required:
            print(f"  required: {_format_list(required)}")
        references = [
            *item["reference_fields"],
            *item["single_reference_fields"],
            *item["nested_reference_fields"],
        ]
        if references:
            print(f"  references: {_format_list(references)}")
        verification_fields = item["verification_fields"]
        if verification_fields:
            print(f"  verification: {_format_list(verification_fields)}")

    print()
    print("Authored specs")
    for type_name in sorted(specs_by_type):
        group = specs_by_type[type_name]
        print(f"- {type_name} ({len(group)})")
        for spec in group:
            print(f"  {spec['id']} - {spec['name']}")
            details = [
                f"type: {spec['type']}",
                f"owner: {spec['owner'] or 'unknown'}",
                f"status: {spec['status']}",
            ]
            print(f"    {', '.join(details)}")
            print(f"    path: {spec['path']}")
    return 0


def _format_list(values: object, *, limit: int = 8) -> str:
    if not isinstance(values, list):
        return ""
    shown = [str(value) for value in values[:limit]]
    if len(values) > limit:
        shown.append(f"+{len(values) - limit} more")
    return ", ".join(shown)


if __name__ == "__main__":
    raise SystemExit(main())
