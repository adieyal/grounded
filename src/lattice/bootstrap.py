from __future__ import annotations

import json
from pathlib import Path

from .models import LatticeConfig
from .registry import default_type_registry_json
from .tags import TAG_SCHEMA


AGENTS_MARKER_START = "<!-- lattice:start -->"
AGENTS_MARKER_END = "<!-- lattice:end -->"

AGENTS_SECTION = f"""\
{AGENTS_MARKER_START}
## Lattice Project Memory

Lattice is the primary source of truth for durable project specs, decisions,
business rules, workflows, examples, and LLM-readable context.
Lattice knowledge units are strongly typed, schema-validated, linked nodes.

The agent is responsible for using, creating, and maintaining this knowledge
base as part of normal project work. Do not treat Lattice as optional
documentation after the fact.

Before implementing or documenting a non-trivial change:

1. Check `lattice.yml` for the configured registry.
2. Search existing Lattice specs for the owner of the idea.
3. Update the existing canonical fact instead of duplicating it.
4. Create a new fact only when no existing owner exists.
5. Use the type registry before inventing a new knowledge-unit type.
6. If the current schema cannot express the fact cleanly, create a `schema_gap`
   instead of smuggling meaning into prose.
7. Reference facts by stable ID from tests, code, docs, and plans.
8. Use domain_object units for durable domain nouns instead of inventing synonyms.
9. Give every knowledge unit a `description` that explains what it is and what
   it is used for.
10. If the change introduces or changes a durable rule, workflow, decision,
   domain object, example, invariant, or assumption, update Lattice in the same
   change.
11. Do not directly edit bundled Lattice templates, validation code, or
   rendering functions for project-specific behavior. Extend through the type
   registry, JSON Schemas, project template overrides, styles, slice metadata,
   or verification specs instead.
12. Regenerate generated views with `lattice render`.
13. Do not manually edit generated Lattice documentation.
14. Run `lattice validate`, `lattice verify`, and `lattice audit`.
15. Report the Lattice IDs changed or explain why no canonical fact changed.

Every idea, fact, rule, workflow, decision, and durable assumption should have
one owner. If another artifact conflicts with a Lattice spec, treat that as
drift and resolve the ownership conflict.
{AGENTS_MARKER_END}
"""


def init_project(
    root: Path,
    *,
    force: bool = False,
    lattice_dir: Path | str = ".lattice",
    update_agents: bool = False,
) -> list[Path]:
    root = root.resolve()
    config = LatticeConfig.default(root, lattice_dir=lattice_dir)
    created: list[Path] = []

    created.extend(
        _write_if_missing(root / "lattice.yml", _lattice_yml(root, config), force=force)
    )
    created.extend(
        _write_if_missing(
            config.type_registry_path, default_type_registry_json(), force=force
        )
    )
    created.extend(
        _write_if_missing(
            config.schemas_dir / "spec.schema.json",
            _spec_schema(),
            force=force,
        )
    )
    created.extend(
        _write_if_missing(
            config.specs_dir.parent / "templates" / "domain_object.json",
            _domain_object_template(),
            force=force,
        )
    )
    created.extend(
        _write_if_missing(
            config.specs_dir.parent / "templates" / "schema_gap.json",
            _schema_gap_template(),
            force=force,
        )
    )
    created.extend(
        _write_if_missing(config.styles_dir / "style.css", _default_css(), force=force)
    )
    created.extend(
        _write_if_missing(
            config.specs_dir / "schema_gaps" / "PROJECT-GAP-001.json",
            _schema_gap(),
            force=force,
        )
    )
    created.extend(
        _write_if_missing(
            config.specs_dir / "verifications" / "PROJECT-VERIFY-001.json",
            _verification(),
            force=force,
        )
    )
    created.extend(
        _write_if_missing(
            root / "skills" / "lattice-project-memory" / "SKILL.md",
            _skill(),
            force=force,
        )
    )
    if update_agents:
        created.extend(_patch_agents(root / "AGENTS.md"))
    return created


def _write_if_missing(path: Path, content: str, *, force: bool) -> list[Path]:
    if path.exists() and not force:
        return []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return [path]


def _patch_agents(path: Path) -> list[Path]:
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if AGENTS_MARKER_START in text and AGENTS_MARKER_END in text:
            before, rest = text.split(AGENTS_MARKER_START, 1)
            _, after = rest.split(AGENTS_MARKER_END, 1)
            path.write_text(
                before.rstrip() + "\n\n" + AGENTS_SECTION + after.lstrip(),
                encoding="utf-8",
            )
        else:
            path.write_text(text.rstrip() + "\n\n" + AGENTS_SECTION, encoding="utf-8")
    else:
        path.write_text(
            "---\nlast_updated: 2026-05-23\n---\n\n# Agent Instructions\n\n"
            + AGENTS_SECTION,
            encoding="utf-8",
        )
    return [path]


def _config_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _lattice_yml(root: Path, config: LatticeConfig) -> str:
    specs_dir = _config_path(root, config.specs_dir)
    type_registry_path = _config_path(root, config.type_registry_path)
    schemas_dir = _config_path(root, config.schemas_dir)
    templates_dir = _config_path(root, config.templates_dir)
    styles_dir = _config_path(root, config.styles_dir)
    generated_docs_dir = _config_path(root, config.generated_docs_dir)
    generated_llm_dir = _config_path(root, config.generated_llm_dir)
    search_index_path = _config_path(root, config.search_index_path)
    return f"""\
# Lattice registry configuration.
specs_dir: {specs_dir}
type_registry_path: {type_registry_path}
schemas_dir: {schemas_dir}
templates_dir: {templates_dir}
styles_dir: {styles_dir}
generated_docs_dir: {generated_docs_dir}
generated_llm_dir: {generated_llm_dir}
search_index_path: {search_index_path}
required_test_kinds:
audit_roots: src,tests,docs,README.md,AGENTS.md
"""


def _json(data: dict[str, object]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _spec_schema() -> str:
    return _json(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Lattice canonical knowledge unit",
            "type": "object",
            "required": ["id", "name", "owner", "status", "description"],
            "anyOf": [{"required": ["type"]}, {"required": ["kind"]}],
            "additionalProperties": True,
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^[A-Z][A-Z0-9-]+-[0-9]{3,}(-EX[0-9]{3,})?$",
                },
                "type": {"type": "string"},
                "kind": {"type": "string"},
                "name": {"type": "string"},
                "owner": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "draft", "retired"]},
                "description": {"type": "string", "minLength": 1},
                "tags": {
                    "type": "array",
                    "items": TAG_SCHEMA,
                    "uniqueItems": True,
                },
                "statement": {"type": "string"},
                "definition": {"type": "string"},
                "preferred_term": {"type": "string"},
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "not": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "object_kind": {"type": "string"},
                "fields": {"type": "array", "items": {"type": "object"}},
                "relationships": {"type": "array", "items": {"type": "string"}},
                "open_questions": {"type": "array", "items": {"type": "string"}},
                "gap": {"type": "string"},
                "suggested_improvement": {"type": "string"},
                "summary": {"type": "string"},
                "references": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "examples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "tests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "links": {"type": "array"},
            },
        }
    )


def _domain_object_template() -> str:
    return _json(
        {
            "id": "PROJECT-DOMAIN-" + "000",
            "type": "domain_object",
            "name": "Preferred Domain Term",
            "owner": "project",
            "status": "draft",
            "description": "Defines the preferred domain term and explains how other project artifacts should use it.",
            "definition": "One concise definition. This is the canonical owner of the domain meaning.",
            "references": [],
            "examples": [],
            "tests": [],
        }
    )


def _schema_gap_template() -> str:
    return _json(
        {
            "id": "PROJECT-GAP-" + "000",
            "type": "schema_gap",
            "name": "Schema gap title",
            "owner": "project",
            "status": "draft",
            "description": "Records a schema limitation so future type registry or renderer work has one canonical owner.",
            "gap": "The durable fact cannot be expressed cleanly with the current type registry or templates.",
            "suggested_improvement": "Add or change a spec type, field, validation rule, or renderer affordance.",
            "affected_kind": "domain_object",
            "references": [],
            "tests": [],
        }
    )


def _default_css() -> str:
    from .render import default_css

    return default_css()


def _project_concept() -> str:
    return _json(
        {
            "id": "PROJECT-CONCEPT-001",
            "type": "concept",
            "name": "Lattice project memory",
            "owner": "project",
            "status": "active",
            "description": "Explains how this project uses Lattice specs as durable project memory.",
            "summary": "Durable project knowledge is owned by canonical Lattice specs and referenced by other artifacts.",
            "references": [],
        }
    )


def _project_rule() -> str:
    return _json(
        {
            "id": "PROJECT-RULE-001",
            "type": "business_rule",
            "name": "Single owner for durable facts",
            "owner": "project",
            "status": "active",
            "description": "Defines the rule that every durable project fact has one source of truth.",
            "statement": "Every durable project fact has exactly one canonical owner; other artifacts reference that owner instead of duplicating it.",
            "references": ["PROJECT-CONCEPT-001"],
        }
    )


def _agent_maintenance_rule() -> str:
    return _json(
        {
            "id": "PROJECT-RULE-002",
            "type": "business_rule",
            "name": "Agents maintain Lattice during project work",
            "owner": "project",
            "status": "active",
            "description": "Defines when agents must update Lattice during project work.",
            "statement": "Agents must use, create, and maintain Lattice specs whenever project work changes durable knowledge.",
            "references": [
                "PROJECT-CONCEPT-001",
                "PROJECT-RULE-001",
            ],
            "tests": ["PROJECT-TEST-001"],
        }
    )


def _schema_gap() -> str:
    return _json(
        {
            "id": "PROJECT-GAP-001",
            "type": "schema_gap",
            "name": "Project-specific fact shapes belong in the type registry",
            "owner": "project",
            "status": "active",
            "description": "Records how project-specific fact shapes should move from schema gaps into the type registry.",
            "gap": "When a durable project fact does not fit existing kinds, agents need a canonical way to capture the mismatch without duplicating meaning elsewhere.",
            "suggested_improvement": "Record the mismatch as a schema_gap, then evolve the configured type registry and templates when the shape becomes stable.",
            "affected_kind": "spec_type",
            "references": [],
            "tests": ["PROJECT-VERIFY-001"],
        }
    )


def _project_example() -> str:
    return _json(
        {
            "id": "PROJECT-RULE-001-EX001",
            "type": "example",
            "name": "Generated docs reference canonical specs",
            "owner": "project",
            "status": "active",
            "description": "Provides an example showing generated docs can repeat canonical facts without owning them.",
            "rule": "PROJECT-RULE-001",
            "intent": "A generated context pack may repeat a rule for consumption, but the canonical statement remains owned by the rule spec.",
            "references": ["PROJECT-RULE-001"],
            "tests": ["PROJECT-TEST-001"],
        }
    )


def _verification() -> str:
    return _json(
        {
            "id": "PROJECT-VERIFY-001",
            "type": "verification",
            "name": "Bootstrap validation",
            "owner": "project",
            "status": "active",
            "description": "Defines the command used to verify that a newly initialized Lattice project is valid.",
            "target": "PROJECT-GAP-001",
            "command": "lattice validate && lattice audit",
            "references": ["PROJECT-GAP-001"],
        }
    )


def _skill() -> str:
    return """\
---
last_updated: 2026-05-27
name: lattice-project-memory
description: Use Lattice as the primary source of truth for specs, durable project knowledge, generated docs, and drift checks.
---

# Lattice Project Memory

## Use This Skill When

- Adding or changing durable project knowledge
- Writing specs, rules, examples, workflows, decisions, or architecture notes
- Defining or changing domain terminology, glossary entries, enum vocabularies, slices, or project-defined tags
- Preparing LLM context from project facts
- Updating tests that prove project rules or examples
- Reviewing drift between docs, code, tests, and specs

## Workflow

1. Read `lattice.yml`.
2. Load the relevant specs under the configured `specs_dir`.
3. Identify the single canonical owner for each idea before editing.
4. Update an existing spec when the fact already has an owner.
5. Create a new spec only when no owner exists.
6. Check the configured type registry before inventing a knowledge-unit type.
7. Capture unmet schema needs as `schema_gap` specs.
8. Check `domain_object` units before naming durable domain concepts in code or docs.
9. Give every knowledge unit a `description` that explains what it is and what it is used for.
10. Use `short_name` when a durable unit needs a concise display alias in generated views.
11. Model closed value sets as `enum` where the current registry supports it.
12. Model scoped documentation views as `slice` units with explicit `members`, slice metadata, and optional `index_template` or `style_path`.
13. Use project-owned `verification` specs for checks against code, files, or generated artifacts; do not encode those checks as template overrides.
14. Reference specs by stable ID from tests, code, and non-generated docs.
15. Update Lattice in the same change when work introduces or changes durable knowledge.
16. Regenerate views with `lattice render`.
17. Run `lattice validate` and `lattice audit`.
18. Report changed Lattice IDs, or state that no durable knowledge changed.

## Non-Negotiables

- Do not duplicate durable facts across artifacts.
- Do not leave Lattice stale after changing durable project meaning.
- Do not define domain terms outside glossary/domain-object specs when the meaning is durable.
- Do not invent new spec kinds without updating the type registry and templates.
- Do not hide a schema limitation in prose; create a `schema_gap` owner.
- Do not directly edit bundled Lattice templates, validation code, or rendering functions for project-specific behavior; extend through the type registry, JSON Schemas, project template overrides, styles, slice metadata, or verification specs instead.
- Do not encode code-existence checks in templates when a verification spec is the right owner.
- Do not manually edit files under the configured generated docs directory.
- Do not invent a competing term, rule, workflow, or decision if a canonical spec exists.
- Treat broken references, stale generated views, and untested required specs as drift.
- If two artifacts disagree, resolve the source-of-truth ownership first.

## Reporting

When reporting work, include changed Lattice IDs and validation results.
"""
