from __future__ import annotations

import re
from collections import defaultdict

from .edge_policy import LEGACY_BACKLINK_FIELDS
from .models import Issue, GroundedConfig, Spec
from .registry import SpecRegistry
from .render import build_rendered_site
from .render_outputs import RenderedSite


REFERENCE_PATTERN = re.compile(
    r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+-\d{3,}(?:-EX\d{3,})?\b"
)
HARD_CODED_STYLE_PATTERN = re.compile(
    r"(?:#[0-9a-fA-F]{3,8}\b|rgb[a]?\(|\b(?:margin|padding|gap|border-radius):\s*[0-9.]+(?:px|rem|em))"
)


def audit(config: GroundedConfig, registry: SpecRegistry) -> list[Issue]:
    site = build_rendered_site(config, registry)
    issues: list[Issue] = []
    issues.extend(audit_generated_views(config, registry, site=site))
    issues.extend(audit_generated_document_coverage(config, registry, site=site))
    issues.extend(audit_documentation_graph(registry))
    issues.extend(audit_style_source(config))
    issues.extend(audit_test_coverage(config, registry))
    issues.extend(audit_unknown_artifact_references(config, registry))
    issues.extend(audit_possible_duplicate_statements(registry))
    issues.extend(audit_semantic_compression_boundaries(registry))
    issues.extend(audit_manual_backlinks(registry))
    return issues


def audit_generated_views(
    config: GroundedConfig, registry: SpecRegistry, *, site: RenderedSite | None = None
) -> list[Issue]:
    if site is None:
        site = build_rendered_site(config, registry)
    stale = site.stale_paths()
    return [
        Issue(
            "GROUNDED-DRIFT-001", f"generated view is stale: {path}", config.root / path
        )
        for path in stale
    ]


def audit_generated_document_coverage(
    config: GroundedConfig, registry: SpecRegistry, *, site: RenderedSite | None = None
) -> list[Issue]:
    if site is None:
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
            "GROUNDED-DOC-GRAPH-004",
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
                    "GROUNDED-DOC-GRAPH-001",
                    registry,
                )
            )
        elif spec.kind == "documentation_set":
            issues.extend(
                _audit_typed_refs(
                    spec,
                    "document_refs",
                    "generated_document",
                    "GROUNDED-DOC-GRAPH-001",
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
                    "GROUNDED-DOC-GRAPH-001",
                    registry,
                )
            )
        elif spec.kind == "asset":
            issues.extend(
                _audit_typed_refs(
                    spec,
                    "used_by",
                    "generated_document",
                    "GROUNDED-DOC-GRAPH-001",
                    registry,
                )
            )
    return issues


def audit_style_source(config: GroundedConfig) -> list[Issue]:
    issues: list[Issue] = []
    source = config.styles_dir / "style.css"
    bundled_source = config.root / "src" / "grounded" / "assets" / "style.css"
    if not source.exists():
        return [Issue("GROUNDED-STYLE-001", "central style.css is missing", source)]
    text = source.read_text(encoding="utf-8")
    if ":root" not in text or "--color-" not in text or "--space-" not in text:
        issues.append(
            Issue(
                "GROUNDED-STYLE-002",
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
                    "GROUNDED-STYLE-003",
                    "hard-coded presentation found outside central style.css; prefer design tokens",
                    path,
                    severity="warning",
                )
            )
    return issues


def _audit_generated_document(spec: Spec) -> list[Issue]:
    issues: list[Issue] = []
    if not _string_value(spec.data.get("output_path")):
        issues.append(
            Issue(
                "GROUNDED-DOC-GRAPH-003",
                f"generated_document {spec.id} must declare output_path",
                spec.path,
            )
        )
    if spec.data.get("format") != "markdown":
        issues.append(
            Issue(
                "GROUNDED-DOC-GRAPH-003",
                f"generated_document {spec.id} must declare format markdown",
                spec.path,
            )
        )
    if spec.data.get("write_mode") not in {"protected_block", "full_file"}:
        issues.append(
            Issue(
                "GROUNDED-DOC-GRAPH-003",
                (
                    f"generated_document {spec.id} must declare write_mode "
                    "protected_block or full_file"
                ),
                spec.path,
            )
        )
    if not _string_value(spec.data.get("renderer")):
        issues.append(
            Issue(
                "GROUNDED-DOC-GRAPH-003",
                f"generated_document {spec.id} must declare renderer",
                spec.path,
            )
        )
    if not _has_source_refs(spec):
        issues.append(
            Issue(
                "GROUNDED-DOC-GRAPH-002",
                f"generated_document {spec.id} must declare source_refs",
                spec.path,
            )
        )
    return issues


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
                "GROUNDED-DOC-GRAPH-002",
                (
                    f"document_section {spec.id} declares content_mode "
                    f"{content_mode} but has no source_refs"
                ),
                spec.path,
            )
        ]
    return []


def audit_test_coverage(config: GroundedConfig, registry: SpecRegistry) -> list[Issue]:
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
                "GROUNDED-COVERAGE-001",
                f"{spec.kind} {spec.id} has no declared test or test_binding",
                spec.path,
            )
        )
    return issues


def audit_unknown_artifact_references(
    config: GroundedConfig, registry: SpecRegistry
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
                        "GROUNDED-REF-004",
                        f"artifact references unknown Grounded id {match}",
                        path,
                    )
                )
    return issues


def _external_example_ids(config: GroundedConfig) -> set[str]:
    examples_dir = config.root / "examples"
    if not examples_dir.exists():
        return set()
    ids: set[str] = set()
    for path in examples_dir.glob("*/grounded/specs/**/*.json"):
        try:
            data = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in REFERENCE_PATTERN.findall(data):
            ids.add(match)
    return ids


def _iter_audit_files(config: GroundedConfig, ignored_parts: set[str]):
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
                    "GROUNDED-OWNERSHIP-001",
                    f"possible duplicate fact statement; candidate owners: {owners}",
                    spec.path,
                    severity="warning",
                )
            )
    return issues


def audit_semantic_compression_boundaries(registry: SpecRegistry) -> list[Issue]:
    issues: list[Issue] = []
    for spec in registry.active_specs:
        if spec.kind == "concept":
            issues.extend(_audit_concept_specificity(spec))
        elif spec.kind == "decision":
            issues.extend(_audit_decision_shape(spec))
        elif spec.kind == "document_section":
            issues.extend(_audit_document_section_truth_boundary(spec))
    return issues


def audit_manual_backlinks(registry: SpecRegistry) -> list[Issue]:
    issues: list[Issue] = []
    for spec in registry.active_specs:
        for field in LEGACY_BACKLINK_FIELDS:
            value = spec.data.get(field)
            has_value = isinstance(value, list) and any(
                isinstance(item, str) and item for item in value
            )
            if not has_value:
                continue
            issues.append(
                Issue(
                    "GROUNDED-EDGE-011",
                    (
                        f"{spec.id}.{field} is a legacy/manual backlink field; "
                        "prefer computed backlinks from normalized edges"
                    ),
                    spec.path,
                    severity="warning",
                )
            )
    return issues


def _audit_concept_specificity(spec: Spec) -> list[Issue]:
    definition = spec.data.get("definition")
    summary = spec.data.get("summary")
    if isinstance(definition, str) and definition.strip():
        return []
    if isinstance(summary, str) and len(summary.strip().split()) >= 12:
        return []
    return [
        Issue(
            "GROUNDED-CONCEPT-001",
            (
                f"concept {spec.id} should have a sharp definition or substantial "
                "summary so concept does not become a catch-all type"
            ),
            spec.path,
            severity="warning",
        )
    ]


DECISION_ALLOWED_FIELDS = frozenset(
    {
        "id",
        "type",
        "kind",
        "name",
        "owner",
        "status",
        "description",
        "summary",
        "context",
        "problem",
        "decision",
        "consequences",
        "references",
        "tests",
        "examples",
        "edges",
        "semantic_layer",
        "links",
        "tags",
        "trust_status",
        "verification_refs",
        "trust_basis",
        "observed_basis",
        "evidence",
    }
)


def _audit_decision_shape(spec: Spec) -> list[Issue]:
    extra_fields = sorted(set(spec.data) - DECISION_ALLOWED_FIELDS)
    if not extra_fields:
        return []
    return [
        Issue(
            "GROUNDED-DECISION-SHAPE-001",
            (f"decision {spec.id} has non-decision fields: {', '.join(extra_fields)}"),
            spec.path,
            severity="warning",
        )
    ]


CLAIM_WORD_PATTERN = re.compile(
    r"\b(?:must|should|required|requires|guarantees|proves|verified|canonical|source of truth)\b",
    re.IGNORECASE,
)


def _audit_document_section_truth_boundary(spec: Spec) -> list[Issue]:
    if _has_source_refs(spec):
        return []
    text_parts = [
        *_text_values(spec.data.get("intro")),
        *_text_values(spec.data.get("outro")),
        *_text_values(spec.data.get("description")),
        *_text_values(spec.data.get("items")),
        *_text_values(spec.data.get("steps")),
        *_text_values(spec.data.get("commands")),
    ]
    text = " ".join(text_parts)
    if not CLAIM_WORD_PATTERN.search(text):
        return []
    return [
        Issue(
            "GROUNDED-DOC-GRAPH-005",
            (
                f"document_section {spec.id} appears to contain canonical claim "
                "language but has no source_refs"
            ),
            spec.path,
            severity="warning",
        )
    ]


def _has_source_refs(spec: Spec) -> bool:
    source_refs = spec.data.get("source_refs", [])
    return isinstance(source_refs, list) and any(
        isinstance(ref, str) and ref for ref in source_refs
    )


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _text_values(value: object) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_text_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_text_values(item))
        return values
    return []


def _normalize_statement(statement: str) -> str:
    value = " ".join(statement.lower().split())
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return value if len(value) >= 30 else ""
