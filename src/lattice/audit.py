from __future__ import annotations

import re
from collections import defaultdict

from .models import Issue, LatticeConfig, Spec
from .registry import SpecRegistry
from .render import build_rendered_site, render_all


REFERENCE_PATTERN = re.compile(
    r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+-\d{3,}(?:-EX\d{3,})?\b"
)
HARD_CODED_STYLE_PATTERN = re.compile(
    r"(?:#[0-9a-fA-F]{3,8}\b|rgb[a]?\(|\b(?:margin|padding|gap|border-radius):\s*[0-9.]+(?:px|rem|em))"
)


def audit(config: LatticeConfig, registry: SpecRegistry) -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(audit_generated_views(config, registry))
    issues.extend(audit_generated_document_coverage(config, registry))
    issues.extend(audit_documentation_graph(registry))
    issues.extend(audit_style_source(config))
    issues.extend(audit_test_coverage(config, registry))
    issues.extend(audit_unknown_artifact_references(config, registry))
    issues.extend(audit_possible_duplicate_statements(registry))
    return issues


def audit_generated_views(config: LatticeConfig, registry: SpecRegistry) -> list[Issue]:
    stale = render_all(config, registry, check=True)
    return [
        Issue(
            "LATTICE-DRIFT-001", f"generated view is stale: {path}", config.root / path
        )
        for path in stale
    ]


def audit_generated_document_coverage(
    config: LatticeConfig, registry: SpecRegistry
) -> list[Issue]:
    site = build_rendered_site(config, registry)
    managed = set(site.outputs) | {block.path for block in site.blocks}
    expected = {config.root / "README.md"}
    docs_dir = config.root / "docs"
    if docs_dir.exists():
        expected.update(
            path
            for path in docs_dir.rglob("*.md")
            if path.is_file() and "images" not in path.relative_to(docs_dir).parts
        )
    return [
        Issue(
            "LATTICE-DOC-GRAPH-004",
            f"documentation file is not managed by a generated_document: {path}",
            path,
        )
        for path in sorted(expected)
        if path.exists() and path not in managed
    ]


def audit_documentation_graph(registry: SpecRegistry) -> list[Issue]:
    issues: list[Issue] = []
    for spec in registry.active_specs:
        if spec.kind == "generated_document":
            issues.extend(_audit_generated_document(spec))
            issues.extend(
                _audit_typed_refs(
                    spec,
                    "section_refs",
                    "document_section",
                    "LATTICE-DOC-GRAPH-001",
                    registry,
                )
            )
        elif spec.kind == "documentation_set":
            issues.extend(
                _audit_typed_refs(
                    spec,
                    "document_refs",
                    "generated_document",
                    "LATTICE-DOC-GRAPH-001",
                    registry,
                )
            )
        elif spec.kind == "document_section":
            issues.extend(_audit_document_section(spec))
            issues.extend(
                _audit_typed_refs(
                    spec,
                    "asset_refs",
                    "asset",
                    "LATTICE-DOC-GRAPH-001",
                    registry,
                )
            )
        elif spec.kind == "asset":
            issues.extend(
                _audit_typed_refs(
                    spec,
                    "used_by",
                    "generated_document",
                    "LATTICE-DOC-GRAPH-001",
                    registry,
                )
            )
    return issues


def audit_style_source(config: LatticeConfig) -> list[Issue]:
    issues: list[Issue] = []
    source = config.styles_dir / "style.css"
    bundled_source = config.root / "src" / "lattice" / "assets" / "style.css"
    if not source.exists():
        return [Issue("LATTICE-STYLE-001", "central style.css is missing", source)]
    text = source.read_text(encoding="utf-8")
    if ":root" not in text or "--color-" not in text or "--space-" not in text:
        issues.append(
            Issue(
                "LATTICE-STYLE-002",
                "central style.css should define design tokens in :root",
                source,
            )
        )

    for path in _iter_audit_files(
        config, {".git", ".venv", "__pycache__", "node_modules", "generated"}
    ):
        if path in {source, bundled_source} or path.suffix not in {".html", ".css"}:
            continue
        candidate = path.read_text(encoding="utf-8", errors="ignore")
        if HARD_CODED_STYLE_PATTERN.search(candidate):
            issues.append(
                Issue(
                    "LATTICE-STYLE-003",
                    "hard-coded presentation found outside central style.css; prefer design tokens",
                    path,
                    severity="warning",
                )
            )
    return issues


def _audit_generated_document(spec: Spec) -> list[Issue]:
    if spec.data.get("write_mode") in {"protected_block", "full_file"}:
        return []
    return [
        Issue(
            "LATTICE-DOC-GRAPH-003",
            (
                f"generated_document {spec.id} must declare write_mode "
                "protected_block or full_file"
            ),
            spec.path,
        )
    ]


def _audit_typed_refs(
    spec: Spec,
    field: str,
    expected_kind: str,
    code: str,
    registry: SpecRegistry,
) -> list[Issue]:
    refs = spec.data.get(field, [])
    if not isinstance(refs, list):
        return []
    issues: list[Issue] = []
    for ref in refs:
        if not isinstance(ref, str):
            continue
        target = registry.get(ref)
        if target is not None and target.kind != expected_kind:
            issues.append(
                Issue(
                    code,
                    (
                        f"{spec.kind} {spec.id} field {field} references {ref}, "
                        f"but expected {expected_kind} and found {target.kind}"
                    ),
                    spec.path,
                )
            )
    return issues


def _audit_document_section(spec: Spec) -> list[Issue]:
    content_mode = spec.data.get("content_mode")
    source_refs = spec.data.get("source_refs", [])
    has_sources = isinstance(source_refs, list) and any(
        isinstance(ref, str) and ref for ref in source_refs
    )
    if content_mode in {"sourced", "mixed"} and not has_sources:
        return [
            Issue(
                "LATTICE-DOC-GRAPH-002",
                (
                    f"document_section {spec.id} declares content_mode "
                    f"{content_mode} but has no source_refs"
                ),
                spec.path,
            )
        ]
    return []


def audit_test_coverage(config: LatticeConfig, registry: SpecRegistry) -> list[Issue]:
    issues: list[Issue] = []
    bindings_by_target: defaultdict[str, list[Spec]] = defaultdict(list)
    for spec in registry.active_specs:
        if spec.kind == "test_binding":
            target = spec.data.get("target")
            if isinstance(target, str):
                bindings_by_target[target].append(spec)

    for spec in registry.active_specs:
        if spec.kind not in config.required_test_kinds:
            continue
        if spec.tests or bindings_by_target.get(spec.id):
            continue
        issues.append(
            Issue(
                "LATTICE-COVERAGE-001",
                f"{spec.kind} {spec.id} has no declared test or test_binding",
                spec.path,
            )
        )
    return issues


def audit_unknown_artifact_references(
    config: LatticeConfig, registry: SpecRegistry
) -> list[Issue]:
    issues: list[Issue] = []
    ignored_parts = {".git", ".venv", "__pycache__", "node_modules", "generated"}
    candidates = list(_iter_audit_files(config, ignored_parts))
    known_ids = set(registry.by_id) | _external_example_ids(config)
    for path in candidates:
        if path.is_relative_to(config.specs_dir):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in REFERENCE_PATTERN.findall(text):
            if match not in known_ids:
                issues.append(
                    Issue(
                        "LATTICE-REF-004",
                        f"artifact references unknown Lattice id {match}",
                        path,
                    )
                )
    return issues


def _external_example_ids(config: LatticeConfig) -> set[str]:
    examples_dir = config.root / "examples"
    if not examples_dir.exists():
        return set()
    ids: set[str] = set()
    for path in examples_dir.glob("*/lattice/specs/**/*.json"):
        try:
            data = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in REFERENCE_PATTERN.findall(data):
            ids.add(match)
    return ids


def _iter_audit_files(config: LatticeConfig, ignored_parts: set[str]):
    suffixes = {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".md",
        ".json",
        ".yml",
        ".yaml",
        ".html",
        ".css",
    }
    for root in config.audit_roots:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            if any(
                part in ignored_parts for part in path.relative_to(config.root).parts
            ):
                continue
            if path.suffix in suffixes:
                yield path


def audit_possible_duplicate_statements(registry: SpecRegistry) -> list[Issue]:
    normalized: defaultdict[str, list[Spec]] = defaultdict(list)
    for spec in registry.active_specs:
        key = _normalize_statement(spec.statement)
        if key:
            normalized[key].append(spec)

    issues: list[Issue] = []
    for specs in normalized.values():
        if len(specs) < 2:
            continue
        owners = ", ".join(spec.id for spec in specs)
        for spec in specs:
            issues.append(
                Issue(
                    "LATTICE-OWNERSHIP-001",
                    f"possible duplicate fact statement; candidate owners: {owners}",
                    spec.path,
                    severity="warning",
                )
            )
    return issues


def _normalize_statement(statement: str) -> str:
    value = " ".join(statement.lower().split())
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return value if len(value) >= 30 else ""
