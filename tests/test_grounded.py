from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import grounded.audit as audit_module
from grounded.audit import audit
from grounded.bindings import bindings_for_spec
from grounded import __version__
from grounded.bootstrap import AGENTS_MARKER_START, init_project
from grounded.cli import main
from grounded.config import load_config
from grounded.registry import default_type_registry_json, load_registry
from grounded.render import (
    default_css,
    field_type_target,
    grounded_link,
    render_all,
    type_nav_label,
)
from grounded.render_documents import render_generated_document
from grounded.verify import verify


class GroundedTests(unittest.TestCase):
    def test_package_version_is_synchronized(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual("1.1.0", pyproject["project"]["version"])
        self.assertEqual(pyproject["project"]["version"], __version__)

    def test_pypi_metadata_and_publish_workflow_are_declared(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        project = pyproject["project"]

        self.assertEqual("grounded", project["name"])
        self.assertEqual("README.md", project["readme"])
        self.assertIn("project-memory", project["keywords"])
        self.assertIn("Topic :: Documentation", project["classifiers"])
        self.assertEqual("Apache-2.0", project["license"])
        self.assertEqual(["LICENSE"], project["license-files"])
        self.assertIn(
            "License :: OSI Approved :: Apache Software License",
            project["classifiers"],
        )
        self.assertIn(
            "Apache License",
            (root / "LICENSE").read_text(encoding="utf-8"),
        )
        self.assertTrue((root / "src/grounded/py.typed").exists())
        self.assertEqual(
            "https://github.com/adieyal/grounded", project["urls"]["Repository"]
        )
        self.assertEqual("grounded.cli:main", project["scripts"]["grounded"])

        workflow = (root / ".github/workflows/pypi.yml").read_text(encoding="utf-8")
        self.assertIn("id-token: write", workflow)
        self.assertIn("uv build", workflow)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", workflow)

    def test_init_creates_specs_and_skill_without_agents_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = init_project(root)

            self.assertIn(root / "grounded.yml", created)
            self.assertTrue(
                (root / ".grounded/specs/schema_gaps/PROJECT-GAP-001.json").exists()
            )
            self.assertTrue(
                (
                    root / ".grounded/specs/verifications/PROJECT-VERIFY-001.json"
                ).exists()
            )
            self.assertTrue((root / ".grounded/registry/spec-types.json").exists())
            type_registry = json.loads(
                (root / ".grounded/registry/spec-types.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                [
                    "asset",
                    "document_section",
                    "documentation_set",
                    "domain_object",
                    "enum",
                    "generated_document",
                    "knowledge_unit",
                    "registry_unit",
                    "schema_gap",
                    "slice",
                    "verification",
                ],
                sorted(type_registry),
            )
            self.assertNotIn("business_entity", type_registry)
            self.assertIn(
                "specs_dir: .grounded/specs",
                (root / "grounded.yml").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "managed_markdown_roots: .grounded/generated/docs",
                (root / "grounded.yml").read_text(encoding="utf-8"),
            )
            self.assertTrue((root / ".grounded/schemas/spec.schema.json").exists())
            self.assertTrue((root / ".grounded/templates/domain_object.json").exists())
            self.assertTrue((root / ".grounded/templates/schema_gap.json").exists())
            self.assertFalse(
                (root / ".grounded/renderers/templates/unit.html.j2").exists()
            )
            self.assertTrue((root / "skills/grounded-project-memory/SKILL.md").exists())
            self.assertFalse((root / "AGENTS.md").exists())

    def test_init_can_update_agents_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = init_project(root, update_agents=True)

            self.assertIn(root / "AGENTS.md", created)
            self.assertIn(
                AGENTS_MARKER_START, (root / "AGENTS.md").read_text(encoding="utf-8")
            )

    def test_init_allows_custom_grounded_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root, grounded_dir="docs/memory")
            config = load_config(root)

            self.assertTrue((root / "docs/memory/specs").exists())
            self.assertEqual(root / "docs/memory/specs", config.specs_dir)
            self.assertIn(
                "specs_dir: docs/memory/specs",
                (root / "grounded.yml").read_text(encoding="utf-8"),
            )

    def test_validate_and_render_check_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            item = {
                "id": "TODO-ITEM-001",
                "kind": "domain_object",
                "name": "Bootstrap Item",
                "owner": "todo",
                "status": "active",
                "description": "A bootstrap domain object used by the round-trip test.",
                "summary": "A bootstrap item.",
            }
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            (specs_dir / f"{item['id']}.json").write_text(
                json.dumps(item), encoding="utf-8"
            )

            config = load_config(root)
            registry = load_registry(config)

            self.assertEqual([], registry.issues)
            self.assertNotEqual([], render_all(config, registry, check=True))
            render_all(config, registry)
            self.assertEqual([], render_all(config, registry, check=True))
            html = (root / ".grounded/generated/docs/index.html").read_text(
                encoding="utf-8"
            )
            css = (root / ".grounded/generated/docs/style.css").read_text(
                encoding="utf-8"
            )
            search = (root / ".grounded/generated/docs/search-index.json").read_text(
                encoding="utf-8"
            )
            markdown = (root / ".grounded/generated/docs/project-memory.md").read_text(
                encoding="utf-8"
            )
            context_pack = (root / ".grounded/generated/llm/context-pack.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("<grounded-main", html)
            self.assertIn("<grounded-unit-card", html)
            self.assertIn("<grounded-search", html)
            self.assertIn("<grounded-theme-toggle", html)
            self.assertIn("grounded-registry", html)
            self.assertIn("grounded-theme", html)
            self.assertIn("grounded-link.js", html)
            self.assertRegex(html, r"grounded-link\.js\?v=[0-9a-f]{12}")
            self.assertIn("Bootstrap Item", html)
            self.assertNotIn("Todo system", html)
            self.assertIn('href="style.css"', html)
            self.assertIn(":root", css)
            self.assertIn(':root[data-theme="dark"]', css)
            self.assertIn("--color-brand-primary: #5645d4;", css)
            self.assertIn("--color-brand-navy: #0a1530;", css)
            self.assertIn("--color-card-tint-lavender: #e6e0f5;", css)
            self.assertIn('--font-serif: "Notion Sans", Inter', css)
            self.assertIn("--font-size-md: 1rem;", css)
            self.assertIn("--radius-md: 0.5rem;", css)
            self.assertIn("--radius-lg: 0.75rem;", css)
            self.assertIn("--radius-pill: 9999px;", css)
            self.assertIn("Bootstrap Item", search)
            self.assertNotIn("last_updated:", markdown)
            self.assertNotIn("last_updated:", context_pack)

    def test_render_escapes_json_in_script_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            spec = {
                "id": "ESCAPE-001",
                "kind": "domain_object",
                "name": 'Danger </script><script>alert("x")</script>',
                "short_name": "Escape",
                "owner": "todo",
                "status": "active",
                "summary": 'Summary with </script><script>alert("x")</script> text.',
            }
            path = root / ".grounded/specs/examples/ESCAPE-001.json"
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(spec), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            html = (root / ".grounded/generated/docs/index.html").read_text(
                encoding="utf-8"
            )

            self.assertIn("\\u003c/script\\u003e", html)
            self.assertNotIn('Danger </script><script>alert("x")</script>', html)

    def test_render_check_reports_obsolete_generated_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            obsolete = root / ".grounded/generated/docs/units/obsolete.html"
            obsolete.write_text("stale", encoding="utf-8")
            legacy_index = root / ".grounded/generated/docs/project-memory.html"
            legacy_index.write_text("legacy", encoding="utf-8")

            stale = render_all(config, registry, check=True)

            self.assertIn(".grounded/generated/docs/units/obsolete.html", stale)
            self.assertIn(".grounded/generated/docs/project-memory.html", stale)

            render_all(config, registry)

            self.assertFalse(obsolete.exists())
            self.assertFalse(legacy_index.exists())

    def test_audit_reuses_rendered_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            config = load_config(root)
            registry = load_registry(config)

            with patch(
                "grounded.audit.build_rendered_site",
                wraps=audit_module.build_rendered_site,
            ) as build_rendered_site:
                audit(config, registry)

            self.assertEqual(1, build_rendered_site.call_count)

    def test_generated_document_blocks_render_from_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            readme = root / "README.md"
            readme.write_text("# Demo\n\nHand-written shell.\n", encoding="utf-8")
            docs_dir = root / ".grounded/specs/docs"
            docs_dir.mkdir(parents=True)
            doc_id = "".join(["PROJECT", "-DOC-001"])
            section_id = "".join(["PROJECT", "-DOC", "-SECTION-001"])
            (docs_dir / f"{doc_id}.json").write_text(
                json.dumps(
                    {
                        "id": doc_id,
                        "kind": "generated_document",
                        "name": "Demo README",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines the generated README block for the demo project.",
                        "output_path": "README.md",
                        "format": "markdown",
                        "renderer": "markdown_document",
                        "write_mode": "protected_block",
                        "audience": "maintainers",
                        "purpose": "Show that README content can be generated from Grounded specs.",
                        "stability": "experimental",
                        "source_refs": ["PROJECT-GAP-001"],
                        "section_refs": [section_id],
                    }
                ),
                encoding="utf-8",
            )
            (docs_dir / f"{section_id}.json").write_text(
                json.dumps(
                    {
                        "id": section_id,
                        "kind": "document_section",
                        "name": "Source-backed README section",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines a source-backed generated README section.",
                        "heading": "Generated from Grounded",
                        "heading_level": 2,
                        "order": 10,
                        "renderer": "source_list",
                        "content_mode": "sourced",
                        "source_refs": ["PROJECT-GAP-001"],
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)

            self.assertIn("README.md", render_all(config, registry, check=True))
            render_all(config, registry)
            self.assertEqual([], render_all(config, registry, check=True))

            text = readme.read_text(encoding="utf-8")
            self.assertIn(f"<!-- grounded:generated:start {doc_id} -->", text)
            self.assertIn("## Generated from Grounded", text)
            self.assertIn("`PROJECT-GAP-001`", text)
            self.assertIn("Source: `PROJECT-GAP-001`", text)
            manifest = json.loads(
                (root / ".grounded/generated/manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(doc_id, manifest["artifacts"]["README.md"]["owner"])
            self.assertEqual(
                "protected_block",
                manifest["artifacts"]["README.md"]["artifact_kind"],
            )

            readme.write_text(
                text.replace("Generated from Grounded", "Edited"), encoding="utf-8"
            )

            self.assertIn("README.md", render_all(config, registry, check=True))

            gap_path = root / ".grounded/specs/schema_gaps/PROJECT-GAP-001.json"
            gap_data = json.loads(gap_path.read_text(encoding="utf-8"))
            gap_data["description"] = "Changed source spec description."
            gap_path.write_text(json.dumps(gap_data), encoding="utf-8")
            registry = load_registry(config)

            self.assertIn("README.md", render_all(config, registry, check=True))
            render_all(config, registry)
            self.assertEqual([], render_all(config, registry, check=True))

    def test_generated_documents_can_own_full_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            output_path = root / "docs/generated.md"
            output_path.parent.mkdir()
            output_path.write_text("stale", encoding="utf-8")
            docs_dir = root / ".grounded/specs/docs"
            docs_dir.mkdir(parents=True)
            doc_id = "".join(["PROJECT", "-DOC-001"])
            section_id = "".join(["PROJECT", "-DOC", "-SECTION-001"])
            (docs_dir / f"{doc_id}.json").write_text(
                json.dumps(
                    {
                        "id": doc_id,
                        "kind": "generated_document",
                        "name": "Generated full file",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines a fully generated Markdown file.",
                        "output_path": "docs/generated.md",
                        "format": "markdown",
                        "renderer": "markdown_document",
                        "write_mode": "full_file",
                        "audience": "maintainers",
                        "purpose": "Prove generated documents can own full files.",
                        "source_refs": ["PROJECT-GAP-001"],
                        "section_refs": [section_id],
                    }
                ),
                encoding="utf-8",
            )
            (docs_dir / f"{section_id}.json").write_text(
                json.dumps(
                    {
                        "id": section_id,
                        "kind": "document_section",
                        "name": "Full file section",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines a source-backed full-file section.",
                        "heading": "Full file",
                        "heading_level": 2,
                        "order": 10,
                        "renderer": "source_summary",
                        "content_mode": "sourced",
                        "source_refs": ["PROJECT-GAP-001"],
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)

            self.assertIn("docs/generated.md", render_all(config, registry, check=True))
            render_all(config, registry)
            self.assertEqual([], render_all(config, registry, check=True))

            text = output_path.read_text(encoding="utf-8")
            self.assertNotIn("grounded:generated:start", text)
            self.assertIn("## Full file", text)
            manifest = json.loads(
                (root / ".grounded/generated/manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "file", manifest["artifacts"]["docs/generated.md"]["artifact_kind"]
            )
            self.assertEqual(
                doc_id, manifest["artifacts"]["docs/generated.md"]["owner"]
            )

    def test_audit_skill_rendered_output_has_fixed_shape(self) -> None:
        skill = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "audit-grounded-knowledge-graph"
            / "SKILL.md"
        )
        text = skill.read_text(encoding="utf-8")

        self.assertIn(
            "This skill is generated by Grounded. Edit the source skill file/specs, not this rendered output.",
            text,
        )
        self.assertIn("## Output Format", text)
        self.assertIn("### 1. Executive Summary", text)
        self.assertIn("### 8. Migration Plan", text)
        self.assertTrue(
            text.rstrip().endswith(
                "What trust status can this graph honestly support, and what evidence would raise it?"
            )
        )

        result = subprocess.run(
            [
                sys.executable,
                str(
                    Path(__file__).resolve().parents[1]
                    / "scripts"
                    / "verify_audit_skill_format.py"
                ),
                "--path",
                str(skill),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_audit_skill_verifier_rejects_bad_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "SKILL.md"
            source = (
                Path(__file__).resolve().parents[1]
                / "skills"
                / "audit-grounded-knowledge-graph"
                / "SKILL.md"
            )
            skill.write_text(
                source.read_text(encoding="utf-8").replace(
                    "### 1. Executive Summary", "### Executive Summary"
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        Path(__file__).resolve().parents[1]
                        / "scripts"
                        / "verify_audit_skill_format.py"
                    ),
                    "--path",
                    str(skill),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn(
                "Output Format ### headings are not in fixed order", result.stdout
            )

    def test_audit_skill_verifier_rejects_previous_name_outside_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "SKILL.md"
            source = (
                Path(__file__).resolve().parents[1]
                / "skills"
                / "audit-grounded-knowledge-graph"
                / "SKILL.md"
            )
            legacy_name = "".join(["Lat", "tice"])
            skill.write_text(
                source.read_text(encoding="utf-8").replace(
                    "Use this skill to review",
                    f"Use this {legacy_name} skill to review",
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        Path(__file__).resolve().parents[1]
                        / "scripts"
                        / "verify_audit_skill_format.py"
                    ),
                    "--path",
                    str(skill),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn(
                "legacy project-name vocabulary appears outside the migration section",
                result.stdout,
            )

    def test_render_generated_skill_reports_missing_source_path_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            config = load_config(root)
            spec = audit_module.Spec(
                id="project-skill-001",
                kind="generated_document",
                path=root / ".grounded/specs/docs/project-skill-001.json",
                data={
                    "id": "project-skill-001",
                    "kind": "generated_document",
                    "name": "Skill output",
                    "owner": "project",
                    "status": "active",
                    "description": "Defines a generated skill artifact.",
                    "output_path": "skills/example/SKILL.md",
                    "format": "markdown",
                    "renderer": "skill_markdown",
                    "write_mode": "full_file",
                    "audience": "maintainers",
                    "purpose": "Exercise render-time source-path handling.",
                    "source_path": "skills/example/missing.source.md",
                    "source_refs": ["project-gap-001"],
                    "section_refs": [],
                },
            )

            with self.assertRaisesRegex(
                FileNotFoundError,
                "project-skill-001 source_path does not exist or is not a file",
            ):
                render_generated_document(spec, load_registry(config), config)

    def test_semantic_document_templates_render_content_first_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            type_registry_path = root / ".grounded/registry/spec-types.json"
            type_registry = json.loads(type_registry_path.read_text(encoding="utf-8"))
            type_registry["decision"] = {
                "extends": "knowledge_unit",
                "renderer": "decision.html.j2",
                "required": [
                    "id",
                    "kind",
                    "name",
                    "owner",
                    "status",
                    "description",
                    "decision",
                ],
                "reference_fields": ["tests"],
                "list_fields": ["tests"],
            }
            type_registry["test_binding"] = {
                "extends": "knowledge_unit",
                "renderer": "test_binding.html.j2",
                "required": [
                    "id",
                    "kind",
                    "name",
                    "owner",
                    "status",
                    "description",
                    "target",
                    "test",
                ],
                "single_reference_fields": ["target"],
            }
            type_registry_path.write_text(json.dumps(type_registry), encoding="utf-8")
            docs_dir = root / ".grounded/specs/docs"
            docs_dir.mkdir(parents=True)
            decision_dir = root / ".grounded/specs/concepts"
            decision_dir.mkdir(parents=True)
            test_dir = root / ".grounded/specs/test_bindings"
            test_dir.mkdir(parents=True)
            doc_id = "".join(["PROJECT", "-DOC-001"])
            section_id = "".join(["PROJECT", "-DOC", "-SECTION-001"])
            decision_id = "".join(["PROJECT", "-DECISION-001"])
            test_id = "".join(["PROJECT", "-TEST-001"])
            (docs_dir / f"{doc_id}.json").write_text(
                json.dumps(
                    {
                        "id": doc_id,
                        "kind": "generated_document",
                        "name": "Generated README",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines a generated README artifact.",
                        "output_path": "README.md",
                        "format": "markdown",
                        "renderer": "markdown_document",
                        "write_mode": "protected_block",
                        "audience": "maintainers",
                        "purpose": "Explain the project from governed specs.",
                        "source_refs": [decision_id],
                        "section_refs": [section_id],
                    }
                ),
                encoding="utf-8",
            )
            (docs_dir / f"{section_id}.json").write_text(
                json.dumps(
                    {
                        "id": section_id,
                        "kind": "document_section",
                        "name": "Decision section",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines a section sourced from a decision.",
                        "heading": "Decision",
                        "heading_level": 2,
                        "order": 10,
                        "renderer": "source_summary",
                        "content_mode": "sourced",
                        "source_refs": [decision_id],
                    }
                ),
                encoding="utf-8",
            )
            (decision_dir / f"{decision_id}.json").write_text(
                json.dumps(
                    {
                        "id": decision_id,
                        "kind": "decision",
                        "name": "Generate docs from specs",
                        "owner": "project",
                        "status": "active",
                        "description": "Documents the generated docs decision.",
                        "decision": "Docs should explain durable source specs before metadata.",
                        "tests": [test_id],
                    }
                ),
                encoding="utf-8",
            )
            (test_dir / f"{test_id}.json").write_text(
                json.dumps(
                    {
                        "id": test_id,
                        "kind": "test_binding",
                        "name": "Semantic template test",
                        "owner": "project",
                        "status": "active",
                        "description": "Binds the semantic template decision to a renderer test.",
                        "target": decision_id,
                        "test": "Render generated_document and decision pages as semantic views.",
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            doc_html = (
                root / ".grounded/generated/docs/units/project-doc-001.html"
            ).read_text(encoding="utf-8")
            decision_html = (
                root / ".grounded/generated/docs/units/project-decision-001.html"
            ).read_text(encoding="utf-8")
            graph_html = (
                root / ".grounded/generated/docs/document-graph.html"
            ).read_text(encoding="utf-8")
            artifact_html = (
                root / ".grounded/generated/docs/artifact-index.html"
            ).read_text(encoding="utf-8")

            self.assertIn("Generated Artifact", doc_html)
            self.assertIn("Projection Sections", doc_html)
            self.assertLess(
                doc_html.index("Generated Artifact"), doc_html.index("Metadata fields")
            )
            self.assertIn("Decision", decision_html)
            self.assertIn("Proof Obligations", decision_html)
            self.assertIn(test_id, decision_html)
            self.assertIn("Docs are projections, not sources.", graph_html)
            self.assertIn("Decision section", graph_html)
            self.assertIn("Artifact Manifest", artifact_html)
            self.assertIn("README.md", artifact_html)

    def test_audit_checks_documentation_graph_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            doc_id = "".join(["PROJECT", "-DOC-001"])
            docs_dir = root / ".grounded/specs/docs"
            docs_dir.mkdir(parents=True)
            (docs_dir / f"{doc_id}.json").write_text(
                json.dumps(
                    {
                        "id": doc_id,
                        "kind": "generated_document",
                        "name": "Invalid README graph",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines an intentionally invalid documentation graph.",
                        "output_path": "README.md",
                        "format": "markdown",
                        "renderer": "markdown_document",
                        "write_mode": "protected_block",
                        "audience": "maintainers",
                        "purpose": "Exercise documentation graph auditing.",
                        "source_refs": ["PROJECT-GAP-001"],
                        "section_refs": ["PROJECT-GAP-001"],
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)
            issues = audit(config, registry)

            self.assertTrue(
                any(issue.code == "GROUNDED-DOC-GRAPH-001" for issue in issues)
            )

    def test_audit_requires_generated_document_projection_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            doc_id = "".join(["PROJECT", "-DOC-001"])
            section_id = "".join(["PROJECT", "-DOC", "-SECTION-001"])
            docs_dir = root / ".grounded/specs/docs"
            docs_dir.mkdir(parents=True)
            (docs_dir / f"{doc_id}.json").write_text(
                json.dumps(
                    {
                        "id": doc_id,
                        "kind": "generated_document",
                        "name": "Missing write mode",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines an intentionally incomplete generated document.",
                        "output_path": "README.md",
                        "format": "markdown",
                        "renderer": "markdown_document",
                        "audience": "maintainers",
                        "purpose": "Exercise write mode auditing.",
                        "section_refs": [section_id],
                    }
                ),
                encoding="utf-8",
            )
            (docs_dir / f"{section_id}.json").write_text(
                json.dumps(
                    {
                        "id": section_id,
                        "kind": "document_section",
                        "name": "Backed section",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines a source-backed section.",
                        "heading": "Backed",
                        "heading_level": 2,
                        "order": 10,
                        "renderer": "source_summary",
                        "content_mode": "sourced",
                        "source_refs": ["PROJECT-GAP-001"],
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)
            issues = audit(config, registry)

            self.assertTrue(
                any(issue.code == "GROUNDED-DOC-GRAPH-003" for issue in issues)
            )
            messages = [issue.message for issue in issues]
            self.assertIn(
                f"generated_document {doc_id} must declare write_mode protected_block or full_file",
                messages,
            )
            self.assertIn(
                f"generated_document {doc_id} must declare source_refs",
                messages,
            )

            doc_path = docs_dir / f"{doc_id}.json"
            doc_data = json.loads(doc_path.read_text(encoding="utf-8"))
            doc_data["write_mode"] = "protected_block"
            doc_data["source_refs"] = ["PROJECT-GAP-001"]
            del doc_data["renderer"]
            doc_path.write_text(json.dumps(doc_data), encoding="utf-8")
            registry = load_registry(config)
            issues = audit(config, registry)

            self.assertIn(
                f"generated_document {doc_id} must declare renderer",
                [issue.message for issue in issues],
            )

    def test_audit_requires_generated_skill_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            docs_dir = root / ".grounded/specs/docs"
            docs_dir.mkdir(parents=True)
            doc_id = "".join(["PROJECT", "-SKILL-001"])
            (docs_dir / f"{doc_id}.json").write_text(
                json.dumps(
                    {
                        "id": doc_id,
                        "kind": "generated_document",
                        "name": "Skill output",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines a generated skill artifact.",
                        "output_path": "skills/example/SKILL.md",
                        "format": "markdown",
                        "renderer": "skill_markdown",
                        "write_mode": "full_file",
                        "audience": "maintainers",
                        "purpose": "Exercise source_path auditing.",
                        "source_refs": ["PROJECT-GAP-001"],
                        "section_refs": [],
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)
            issues = audit(config, registry)

            self.assertIn(
                f"generated_document {doc_id} must declare source_path for skill_markdown",
                [issue.message for issue in issues],
            )

    def test_audit_checks_only_configured_markdown_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            generated_docs_dir = root / ".grounded/generated/docs"
            generated_docs_dir.mkdir(parents=True, exist_ok=True)
            (generated_docs_dir / "manual.md").write_text(
                "# Generated doc\n", encoding="utf-8"
            )
            (root / "README.md").write_text("# Manual\n", encoding="utf-8")
            docs_dir = root / "docs"
            docs_dir.mkdir()
            (docs_dir / "manual.md").write_text("# Manual doc\n", encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            issues = audit(config, registry)

            unmanaged_paths = {
                issue.path.relative_to(root).as_posix()
                for issue in issues
                if issue.code == "GROUNDED-DOC-GRAPH-004" and issue.path is not None
            }
            self.assertIn(".grounded/generated/docs/manual.md", unmanaged_paths)
            self.assertNotIn("README.md", unmanaged_paths)
            self.assertNotIn("docs/manual.md", unmanaged_paths)

            grounded_yml = root / "grounded.yml"
            grounded_yml.write_text(
                grounded_yml.read_text(encoding="utf-8").replace(
                    "managed_markdown_roots: .grounded/generated/docs",
                    "managed_markdown_roots: .grounded/generated/docs,README.md,docs",
                ),
                encoding="utf-8",
            )
            config = load_config(root)
            registry = load_registry(config)
            issues = audit(config, registry)

            unmanaged_paths = {
                issue.path.relative_to(root).as_posix()
                for issue in issues
                if issue.code == "GROUNDED-DOC-GRAPH-004" and issue.path is not None
            }
            self.assertIn(".grounded/generated/docs/manual.md", unmanaged_paths)
            self.assertIn("README.md", unmanaged_paths)
            self.assertIn("docs/manual.md", unmanaged_paths)

    def test_audit_rejects_ungrounded_sourced_document_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            section_id = "".join(["PROJECT", "-DOC", "-SECTION-001"])
            docs_dir = root / ".grounded/specs/docs"
            docs_dir.mkdir(parents=True)
            (docs_dir / f"{section_id}.json").write_text(
                json.dumps(
                    {
                        "id": section_id,
                        "kind": "document_section",
                        "name": "Ungrounded sourced section",
                        "owner": "project",
                        "status": "active",
                        "description": "Defines an intentionally ungrounded document section.",
                        "heading": "Ungrounded",
                        "heading_level": 2,
                        "order": 10,
                        "renderer": "source_summary",
                        "content_mode": "sourced",
                        "source_refs": [],
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)
            issues = audit(config, registry)

            self.assertTrue(
                any(issue.code == "GROUNDED-DOC-GRAPH-002" for issue in issues)
            )

    def test_field_type_target_requires_exact_display_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self.assertIsNone(
                field_type_target("domain_object", load_registry(load_config(root)))
            )

            spec_path = root / ".grounded/specs/examples/TODO-ITEM-001.json"
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(
                json.dumps(
                    {
                        "id": "TODO-ITEM-001",
                        "kind": "domain_object",
                        "name": "Todo Item",
                        "owner": "todo",
                        "status": "active",
                        "description": "A user-visible task in the todo list.",
                    }
                ),
                encoding="utf-8",
            )

            registry = load_registry(load_config(root))

            self.assertIsNotNone(field_type_target("Todo Item", registry))

    def test_registry_type_label_uses_grounded_types(self) -> None:
        self.assertEqual("Grounded Types", type_nav_label("registry_type"))
        self.assertEqual("Grounded Types", type_nav_label("spec_type"))

    def test_render_rejects_slug_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            first_id = "".join(["FOO", "_BAR_001"])
            second_id = "".join(["FOO", "-BAR-001"])
            first = {
                "id": first_id,
                "kind": "domain_object",
                "name": "First Object",
                "owner": "todo",
                "status": "active",
                "summary": "First.",
            }
            second = {
                "id": second_id,
                "kind": "domain_object",
                "name": "Second Object",
                "owner": "todo",
                "status": "active",
                "summary": "Second.",
            }
            first_path = root / ".grounded/specs/examples" / f"{first_id}.json"
            first_path.parent.mkdir(exist_ok=True)
            first_path.write_text(json.dumps(first), encoding="utf-8")
            second_path = root / ".grounded/specs/examples" / f"{second_id}.json"
            second_path.write_text(json.dumps(second), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)

            with self.assertRaises(ValueError):
                render_all(config, registry)

    def test_todo_example_is_a_separate_grounded_project(self) -> None:
        root = Path(__file__).resolve().parents[1]
        distribution_todo_specs = list((root / "grounded/specs").rglob("TODO-*.json"))
        example_root = root / "examples/todo"
        example_config = load_config(example_root)
        example_registry = load_registry(example_config)

        self.assertEqual([], distribution_todo_specs)
        self.assertTrue((example_root / "grounded.yml").exists())
        self.assertTrue((example_root / "grounded/specs/TODO-ITEM-001.json").exists())
        self.assertEqual([], example_registry.issues)
        self.assertIn("TODO-ITEM-001", example_registry.by_id)
        self.assertEqual(
            example_root / "grounded/registry/spec-types.json",
            example_config.type_registry_path,
        )

    def test_default_type_registry_is_core_only(self) -> None:
        type_registry = json.loads(default_type_registry_json())

        self.assertEqual(
            [
                "asset",
                "document_section",
                "documentation_set",
                "domain_object",
                "enum",
                "generated_document",
                "knowledge_unit",
                "registry_unit",
                "schema_gap",
                "slice",
                "verification",
            ],
            sorted(type_registry),
        )
        self.assertNotIn("business_entity", type_registry)
        self.assertNotIn("lifecycle_type", type_registry)

    def test_registry_unit_is_minimal_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            spec_id = "".join(["BASE", "-UNIT-001"])
            spec_path = root / ".grounded/specs/examples" / f"{spec_id}.json"
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(
                json.dumps(
                    {
                        "id": spec_id,
                        "type": "registry_unit",
                        "name": "Base Unit",
                        "status": "active",
                    }
                ),
                encoding="utf-8",
            )

            registry = load_registry(load_config(root))

            self.assertEqual([], registry.issues)

    def test_search_cli_finds_entities_and_related_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            item_id = "TODO-ITEM-001"
            rule_id = "TODO" + "-RULE-001"
            item = {
                "id": item_id,
                "kind": "domain_object",
                "name": "Todo Item",
                "short_name": "Task",
                "owner": "todo",
                "status": "active",
                "description": "A user-visible task in the todo list.",
                "definition": "A todo item is a task that can move through lifecycle states.",
            }
            rule = {
                "id": rule_id,
                "kind": "schema_gap",
                "name": "Todo lifecycle rule",
                "owner": "todo",
                "status": "active",
                "description": "Documents a missing lifecycle rule for todo items.",
                "gap": "Todo item lifecycle rules need a stronger spec type.",
                "suggested_improvement": "Add a lifecycle rule type.",
                "references": [item_id],
            }
            (specs_dir / f"{item_id}.json").write_text(
                json.dumps(item), encoding="utf-8"
            )
            (specs_dir / f"{rule_id}.json").write_text(
                json.dumps(rule), encoding="utf-8"
            )

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    ["--root", str(root), "search", "task", "--kind", "entities"]
                )

            self.assertEqual(0, result)
            self.assertIn("Todo Item", output.getvalue())
            self.assertIn("exact id/name match", output.getvalue())

            output = StringIO()
            with redirect_stdout(output):
                result = main(["--root", str(root), "specs", "--uses", "todo item"])

            self.assertEqual(0, result)
            self.assertIn("Todo lifecycle rule", output.getvalue())
            self.assertNotIn("Todo Item\n", output.getvalue())

            output = StringIO()
            with redirect_stdout(output):
                result = main(["--root", str(root), "check-new", "todo item", "--json"])

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(
                "Likely exists already; inspect the top entity before adding a new concept.",
                payload["recommendation"],
            )
            self.assertEqual(item_id, payload["entity_matches"][0]["id"])

    def _write_context_fixture(self, root: Path) -> tuple[str, str, str]:
        specs_dir = root / ".grounded/specs/examples"
        specs_dir.mkdir(parents=True)
        item_id = "TODO-ITEM-001"
        rule_id = "TODO" + "-RULE-001"
        status_id = "TODO-STATUS-001"
        (specs_dir / f"{item_id}.json").write_text(
            json.dumps(
                {
                    "id": item_id,
                    "kind": "domain_object",
                    "name": "Todo Item",
                    "short_name": "Task",
                    "owner": "todo",
                    "status": "active",
                    "description": "A user-visible task in the todo list.",
                }
            ),
            encoding="utf-8",
        )
        (specs_dir / f"{rule_id}.json").write_text(
            json.dumps(
                {
                    "id": rule_id,
                    "kind": "schema_gap",
                    "name": "Todo item requires status",
                    "owner": "todo",
                    "status": "active",
                    "description": "Documents a missing status rule for todo items.",
                    "gap": "Todo items need a stronger status rule.",
                    "suggested_improvement": "Add a todo status rule type.",
                    "references": [item_id, status_id],
                }
            ),
            encoding="utf-8",
        )
        (specs_dir / f"{status_id}.json").write_text(
            json.dumps(
                {
                    "id": status_id,
                    "kind": "domain_object",
                    "name": "Todo Status",
                    "owner": "todo",
                    "status": "active",
                    "description": "A value that describes todo item progress.",
                }
            ),
            encoding="utf-8",
        )
        return item_id, rule_id, status_id

    def _install_bindable_fixture_types(self, root: Path) -> None:
        registry_path = root / ".grounded/registry/spec-types.json"
        type_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        type_registry["page_view"] = {
            "extends": "knowledge_unit",
            "capabilities": ["bindable"],
            "binding_field_mappings": [
                {
                    "field": "file",
                    "role": "implementation",
                    "target": {
                        "kind": "file",
                        "media_type": "text/x-typescript",
                    },
                    "cardinality": "one",
                    "validation": {
                        "path_exists": True,
                        "missing": "error",
                    },
                    "context": {
                        "include_by_default": True,
                        "priority": 80,
                    },
                },
                {
                    "field": "tests",
                    "role": "test",
                    "target": {"kind": "file"},
                    "cardinality": "many",
                    "validation": {
                        "path_exists": True,
                        "missing": "warning",
                    },
                    "context": {
                        "include_by_default": False,
                        "priority": 60,
                    },
                },
            ],
            "schema": {
                "type": "object",
                "required": [
                    "id",
                    "name",
                    "owner",
                    "status",
                    "description",
                    "file",
                ],
                "properties": {
                    "type": {"const": "page_view"},
                    "kind": {"const": "page_view"},
                    "file": {"type": "string", "minLength": 1},
                    "tests": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "bindings": {"type": "array"},
                },
                "additionalProperties": True,
            },
            "required": [
                "id",
                "name",
                "owner",
                "status",
                "description",
                "file",
            ],
            "search_fields": ["id", "name", "description", "file", "tests"],
            "reference_fields": [],
            "list_fields": ["tests"],
        }
        type_registry["page_query"] = {
            "extends": "knowledge_unit",
            "capabilities": ["bindable"],
            "binding_field_mappings": [
                {
                    "field": "repository_file",
                    "role": "implementation",
                    "target": {
                        "kind": "file",
                        "media_type": "text/x-typescript",
                    },
                    "cardinality": "one",
                    "validation": {
                        "path_exists": True,
                        "missing": "error",
                    },
                    "context": {
                        "include_by_default": True,
                        "priority": 70,
                    },
                }
            ],
            "schema": {
                "type": "object",
                "required": [
                    "id",
                    "name",
                    "owner",
                    "status",
                    "description",
                    "repository_file",
                ],
                "properties": {
                    "type": {"const": "page_query"},
                    "kind": {"const": "page_query"},
                    "repository_file": {"type": "string", "minLength": 1},
                },
                "additionalProperties": True,
            },
            "required": [
                "id",
                "name",
                "owner",
                "status",
                "description",
                "repository_file",
            ],
            "search_fields": [
                "id",
                "name",
                "description",
                "repository_file",
            ],
            "reference_fields": [],
        }
        type_registry["plain_note"] = {
            "extends": "knowledge_unit",
            "schema": {
                "type": "object",
                "required": [
                    "id",
                    "name",
                    "owner",
                    "status",
                    "description",
                ],
                "properties": {
                    "type": {"const": "plain_note"},
                    "kind": {"const": "plain_note"},
                    "bindings": {"type": "array"},
                    "file": {"type": "string"},
                    "tests": {"type": "array"},
                },
                "additionalProperties": True,
            },
            "required": [
                "id",
                "name",
                "owner",
                "status",
                "description",
            ],
            "search_fields": ["id", "name", "description", "file", "tests"],
            "reference_fields": [],
        }
        registry_path.write_text(json.dumps(type_registry, indent=2), encoding="utf-8")

    def _write_binding_fixture(self, root: Path) -> tuple[str, str]:
        self._install_bindable_fixture_types(root)
        (root / "frontend/src/pages/home").mkdir(parents=True)
        (root / "frontend/tests/component").mkdir(parents=True)
        (root / "frontend/src/pages/home/home-page.ts").write_text(
            "export class HomePageElement {}\n",
            encoding="utf-8",
        )
        (root / "frontend/tests/component/home-page.test.ts").write_text(
            "test('home page', () => {});\n",
            encoding="utf-8",
        )
        specs_dir = root / ".grounded/specs/examples"
        specs_dir.mkdir(parents=True)
        view_id = "PAGE-VIEW-TMP"
        query_id = "PAGE-QUERY-TMP"
        (specs_dir / f"{view_id}.json").write_text(
            json.dumps(
                {
                    "id": view_id,
                    "kind": "page_view",
                    "name": "Home Page View",
                    "owner": "web",
                    "status": "active",
                    "description": "Renders the home page.",
                    "file": "frontend/src/pages/home/home-page.ts",
                    "tests": ["frontend/tests/component/home-page.test.ts"],
                    "references": [query_id],
                }
            ),
            encoding="utf-8",
        )
        (root / "frontend/src/pages/home/home-query.ts").write_text(
            "export const homeQuery = {};\n",
            encoding="utf-8",
        )
        (specs_dir / f"{query_id}.json").write_text(
            json.dumps(
                {
                    "id": query_id,
                    "kind": "page_query",
                    "name": "Home Page Query",
                    "owner": "web",
                    "status": "active",
                    "description": "Loads home page data.",
                    "repository_file": "frontend/src/pages/home/home-query.ts",
                }
            ),
            encoding="utf-8",
        )
        return view_id, query_id

    def test_context_cli_builds_focused_llm_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            item_id, rule_id, status_id = self._write_context_fixture(root)
            output = StringIO()
            with redirect_stdout(output):
                result = main(["--root", str(root), "context", "task"])

            self.assertEqual(0, result)
            text = output.getvalue()
            self.assertIn("# Grounded Focused Context", text)
            self.assertIn(f"Seed: `{item_id}`", text)
            self.assertIn("Warning: START was resolved by search", text)
            self.assertIn(f"### `{rule_id}`", text)
            self.assertIn(f"{rule_id} mentions -> {item_id}", text)
            self.assertIn(".grounded/specs/examples/TODO-ITEM-001.json", text)
            self.assertNotIn(str(root), text)

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    ["--root", str(root), "context", rule_id, "--depth", "1", "--json"]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(rule_id, payload["seed"]["id"])
            self.assertEqual("exact_id", payload["seed_resolution"])
            self.assertEqual(
                f".grounded/specs/examples/{rule_id}.json",
                payload["seed"]["path"],
            )
            self.assertEqual(
                [rule_id, item_id, status_id],
                [item["id"] for item in payload["items"]],
            )

    def test_context_cli_prefers_exact_id_over_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._write_context_fixture(root)
            exact_id = "TASK"
            exact_path = root / ".grounded/specs/examples/TASK.json"
            exact_path.write_text(
                json.dumps(
                    {
                        "id": exact_id,
                        "kind": "domain_object",
                        "name": "Exact Task Entity",
                        "owner": "todo",
                        "status": "active",
                        "description": "The exact ID must win over fuzzy task matches.",
                    }
                ),
                encoding="utf-8",
            )

            output = StringIO()
            with redirect_stdout(output):
                result = main(["--root", str(root), "context", exact_id, "--json"])

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(exact_id, payload["seed"]["id"])
            self.assertEqual("exact id match", payload["seed_reason"])

    def test_context_cli_does_not_fuzzy_select_retired_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            item_id, _, _ = self._write_context_fixture(root)
            retired_ids = tuple(f"TASK-OLD-{index:03d}" for index in range(10))
            for retired_id in retired_ids:
                retired_path = root / f".grounded/specs/examples/{retired_id}.json"
                retired_path.write_text(
                    json.dumps(
                        {
                            "id": retired_id,
                            "kind": "domain_object",
                            "name": "Task",
                            "owner": "todo",
                            "status": "retired",
                            "description": "A retired task concept.",
                        }
                    ),
                    encoding="utf-8",
                )

            output = StringIO()
            with redirect_stdout(output):
                result = main(["--root", str(root), "context", "task", "--json"])

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(item_id, payload["seed"]["id"])
            self.assertTrue(
                set(retired_ids).isdisjoint({item["id"] for item in payload["items"]})
            )

    def test_context_cli_reports_no_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._write_context_fixture(root)
            output = StringIO()
            errors = StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                result = main(["--root", str(root), "context", "no-such-context"])

            self.assertEqual(1, result)
            self.assertEqual("", output.getvalue())
            self.assertIn(
                "No context seed found for: no-such-context", errors.getvalue()
            )

    def test_context_cli_depth_zero_and_limit_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            item_id, rule_id, status_id = self._write_context_fixture(root)

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        rule_id,
                        "--depth",
                        "0",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual([rule_id], [item["id"] for item in payload["items"]])

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        rule_id,
                        "--depth",
                        "1",
                        "--limit",
                        "2",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(
                [rule_id, item_id],
                [item["id"] for item in payload["items"]],
            )
            self.assertNotIn(status_id, [item["id"] for item in payload["items"]])

    def test_context_cli_rejects_invalid_depth_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._write_context_fixture(root)

            for args, expected_error in (
                (["--depth", "-1"], "--depth must be >= 0"),
                (["--limit", "0"], "--limit must be >= 1"),
                (["--limit", "-5"], "--limit must be >= 1"),
            ):
                with self.subTest(args=args):
                    errors = StringIO()
                    with redirect_stderr(errors):
                        result = main(["--root", str(root), "context", "task", *args])

                    self.assertEqual(2, result)
                    self.assertIn(expected_error, errors.getvalue())

    def test_context_cli_refuses_registry_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            missing_id = "UNKNOWN" + "-001"
            (specs_dir / "BROKEN-001.json").write_text(
                json.dumps(
                    {
                        "id": "BROKEN-001",
                        "kind": "domain_object",
                        "name": "Broken",
                        "owner": "todo",
                        "status": "active",
                        "description": "A broken unit for registry issue testing.",
                        "references": [missing_id],
                    }
                ),
                encoding="utf-8",
            )

            errors = StringIO()
            with redirect_stderr(errors):
                result = main(["--root", str(root), "context", "Broken"])

            self.assertEqual(1, result)
            self.assertIn("GROUNDED-REF", errors.getvalue())

    def test_context_cli_outputs_registry_declared_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            view_id, query_id = self._write_binding_fixture(root)

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        view_id,
                        "--depth",
                        "0",
                        "--include-bindings",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(view_id, payload["seed"]["id"])
            bindings = payload["items"][0]["bindings"]
            self.assertEqual(
                [f"{view_id}:file", f"{view_id}:tests:0"],
                [binding["id"] for binding in bindings],
            )
            self.assertEqual(
                "frontend/src/pages/home/home-page.ts",
                bindings[0]["target"]["path"],
            )
            self.assertTrue(bindings[0]["binding_included"])
            self.assertEqual("implementation", bindings[0]["role"])
            self.assertTrue(bindings[1]["binding_included"])
            self.assertEqual("test", bindings[1]["role"])
            self.assertFalse(bindings[1]["artifact_included"])
            self.assertEqual(
                "artifact_content_not_requested",
                bindings[1]["artifact_omitted_reason"],
            )
            self.assertEqual([], payload["items"][0]["binding_diagnostics"])

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        view_id,
                        "--depth",
                        "0",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertNotIn("bindings", payload["items"][0])
            self.assertNotIn("binding_diagnostics", payload["items"][0])

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        query_id,
                        "--depth",
                        "0",
                        "--include-bindings",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(
                f"{query_id}:repository_file",
                payload["items"][0]["bindings"][0]["id"],
            )

    def test_context_cli_resolves_changed_files_from_declared_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            view_id, _ = self._write_binding_fixture(root)

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "--changed-files",
                        "frontend/src/pages/home/home-page.ts",
                        "--depth",
                        "0",
                        "--include-bindings",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual("changed_files", payload["seed_resolution"])
            self.assertEqual(view_id, payload["seed"]["id"])
            self.assertEqual([view_id], [item["id"] for item in payload["items"]])
            self.assertEqual(
                ["declared file binding match: frontend/src/pages/home/home-page.ts"],
                payload["items"][0]["reasons"],
            )
            self.assertEqual(
                "frontend/src/pages/home/home-page.ts",
                payload["items"][0]["bindings"][0]["target"]["path"],
            )

    def test_context_cli_changed_files_accepts_absolute_project_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            view_id, _ = self._write_binding_fixture(root)
            changed_path = root / "frontend/src/pages/home/home-page.ts"

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "--changed-files",
                        str(changed_path),
                        "--depth",
                        "0",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(view_id, payload["seed"]["id"])
            self.assertNotIn("bindings", payload["items"][0])

    def test_context_cli_changed_files_can_seed_multiple_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            view_id, query_id = self._write_binding_fixture(root)

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "--changed-files",
                        "frontend/src/pages/home/home-page.ts",
                        "frontend/src/pages/home/home-query.ts",
                        "--depth",
                        "0",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(
                [view_id, query_id], [item["id"] for item in payload["items"]]
            )
            self.assertEqual([0, 0], [item["distance"] for item in payload["items"]])

    def test_context_cli_changed_files_reports_no_binding_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._write_binding_fixture(root)
            errors = StringIO()

            with redirect_stderr(errors):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "--changed-files",
                        "frontend/src/pages/home/not-bound.ts",
                    ]
                )

            self.assertEqual(1, result)
            self.assertIn(
                "No context seed found for changed files: "
                "frontend/src/pages/home/not-bound.ts",
                errors.getvalue(),
            )

    def test_context_cli_requires_start_or_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            errors = StringIO()

            with redirect_stderr(errors):
                result = main(["--root", str(root), "context"])

            self.assertEqual(2, result)
            self.assertIn(
                "Provide either START or --changed-files PATH [PATH ...]",
                errors.getvalue(),
            )

            errors = StringIO()
            with redirect_stderr(errors):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "anything",
                        "--changed-files",
                        "frontend/src/pages/home/home-page.ts",
                    ]
                )

            self.assertEqual(2, result)
            self.assertIn(
                "Provide either START or --changed-files PATH [PATH ...]",
                errors.getvalue(),
            )

    def test_binding_paths_normalize_backslashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            view_id, _ = self._write_binding_fixture(root)
            spec_path = root / f".grounded/specs/examples/{view_id}.json"
            spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
            spec_data["file"] = "frontend\\src\\pages\\home\\home-page.ts"
            spec_path.write_text(json.dumps(spec_data), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        view_id,
                        "--depth",
                        "0",
                        "--include-bindings",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual(
                "frontend/src/pages/home/home-page.ts",
                payload["items"][0]["bindings"][0]["target"]["path"],
            )

    def test_context_cli_markdown_shows_binding_paths_without_artifact_content(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            view_id, _ = self._write_binding_fixture(root)

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        view_id,
                        "--depth",
                        "0",
                        "--include-bindings",
                    ]
                )

            self.assertEqual(0, result)
            text = output.getvalue()
            self.assertNotIn("## Bindings", text)
            self.assertIn("- Bindings:", text)
            self.assertIn(
                "implementation: `frontend/src/pages/home/home-page.ts` "
                "_(content not included)_",
                text,
            )
            self.assertIn(
                "test: `frontend/tests/component/home-page.test.ts` "
                "_(content not included)_",
                text,
            )
            self.assertNotIn(str(root), text)

    def test_binding_validation_is_opt_in_by_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._install_bindable_fixture_types(root)
            type_registry = json.loads(
                (root / ".grounded/registry/spec-types.json").read_text(
                    encoding="utf-8"
                )
            )
            knowledge_unit_schema = type_registry["knowledge_unit"]["schema"]
            self.assertNotIn("bindings", knowledge_unit_schema.get("properties", {}))
            self.assertNotIn("binding_field_mappings", type_registry["knowledge_unit"])
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            (specs_dir / "NOTE-001.json").write_text(
                json.dumps(
                    {
                        "id": "NOTE-001",
                        "kind": "plain_note",
                        "name": "Plain Note",
                        "owner": "docs",
                        "status": "active",
                        "description": "A plain note with fields named like bindings.",
                        "file": "does/not/become/a/binding.ts",
                        "tests": ["NOTE-TEST-TMP"],
                    }
                ),
                encoding="utf-8",
            )
            (specs_dir / "NOTE-TEST-TMP.json").write_text(
                json.dumps(
                    {
                        "id": "NOTE-TEST-TMP",
                        "kind": "plain_note",
                        "name": "Plain Note Test",
                        "owner": "docs",
                        "status": "active",
                        "description": "A spec-shaped test reference.",
                    }
                ),
                encoding="utf-8",
            )

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "NOTE-001",
                        "--include-bindings",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            self.assertEqual([], payload["items"][0]["bindings"])

            (specs_dir / "NOTE-002.json").write_text(
                json.dumps(
                    {
                        "id": "NOTE-002",
                        "kind": "plain_note",
                        "name": "Plain Note With Binding",
                        "owner": "docs",
                        "status": "active",
                        "description": "A non-bindable spec with explicit bindings.",
                        "bindings": [
                            {
                                "role": "implementation",
                                "target": {
                                    "kind": "file",
                                    "path": "README.md",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            errors = StringIO()
            with redirect_stderr(errors):
                result = main(["--root", str(root), "validate"])

            self.assertEqual(1, result)
            self.assertIn("GROUNDED-BINDING-001", errors.getvalue())

    def test_bindable_type_can_declare_explicit_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._install_bindable_fixture_types(root)
            (root / "frontend/src/pages/home").mkdir(parents=True)
            (root / "frontend/src/pages/home/explicit-home.ts").write_text(
                "export class ExplicitHomePageElement {}\n",
                encoding="utf-8",
            )
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            (specs_dir / "PAGE-VIEW-EXPLICIT.json").write_text(
                json.dumps(
                    {
                        "id": "PAGE-VIEW-EXPLICIT",
                        "kind": "page_view",
                        "name": "Explicit Home Page View",
                        "owner": "web",
                        "status": "active",
                        "description": "Declares explicit binding metadata.",
                        "file": "frontend/src/pages/home/explicit-home.ts",
                        "bindings": [
                            {
                                "id": "PAGE-VIEW-EXPLICIT:explicit-file",
                                "role": "implementation",
                                "target": {
                                    "kind": "file",
                                    "path": "frontend/src/pages/home/explicit-home.ts",
                                    "media_type": "text/x-typescript",
                                },
                                "include": {
                                    "default": True,
                                    "priority": 90,
                                },
                                "validation": {
                                    "path_exists": True,
                                    "missing": "error",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "PAGE-VIEW-EXPLICIT",
                        "--depth",
                        "0",
                        "--include-bindings",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            binding_ids = [binding["id"] for binding in payload["items"][0]["bindings"]]
            self.assertIn("PAGE-VIEW-EXPLICIT:explicit-file", binding_ids)
            self.assertIn("PAGE-VIEW-EXPLICIT:file", binding_ids)

    def test_binding_validation_rejects_unsafe_paths_and_cardinality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._install_bindable_fixture_types(root)
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)

            cases = [
                ("ABSOLUTE-PATH", "/tmp/home-page.ts", "repo-relative"),
                ("WINDOWS-DRIVE-PATH", "C:\\tmp\\home-page.ts", "repo-relative"),
                ("WINDOWS-DRIVE-RELATIVE-PATH", "C:tmp\\home-page.ts", "repo-relative"),
                (
                    "WINDOWS-UNC-PATH",
                    "\\\\server\\share\\home-page.ts",
                    "repo-relative",
                ),
                ("TILDE-PATH", "~/home-page.ts", "repo-relative"),
                ("ESCAPING-PATH", "../home-page.ts", "must not contain '..'"),
            ]
            for spec_id, file_path, expected in cases:
                with self.subTest(spec_id=spec_id):
                    for existing in specs_dir.glob("*.json"):
                        existing.unlink()
                    (specs_dir / f"{spec_id}.json").write_text(
                        json.dumps(
                            {
                                "id": spec_id,
                                "kind": "page_view",
                                "name": spec_id,
                                "owner": "web",
                                "status": "active",
                                "description": "An invalid page view binding.",
                                "file": file_path,
                            }
                        ),
                        encoding="utf-8",
                    )

                    errors = StringIO()
                    with redirect_stderr(errors):
                        result = main(["--root", str(root), "validate"])

                    self.assertEqual(1, result)
                    self.assertIn("GROUNDED-BINDING-008", errors.getvalue())
                    self.assertIn(expected, errors.getvalue())

            for existing in specs_dir.glob("*.json"):
                existing.unlink()
            (specs_dir / "BAD-CARDINALITY-TMP.json").write_text(
                json.dumps(
                    {
                        "id": "BAD-CARDINALITY-TMP",
                        "kind": "page_view",
                        "name": "Bad Cardinality",
                        "owner": "web",
                        "status": "active",
                        "description": "A page view with the wrong binding shape.",
                        "file": ["frontend/src/pages/home/home-page.ts"],
                    }
                ),
                encoding="utf-8",
            )

            errors = StringIO()
            with redirect_stderr(errors):
                result = main(["--root", str(root), "validate"])

            self.assertEqual(1, result)
            self.assertIn("must be a scalar binding path", errors.getvalue())

            for existing in specs_dir.glob("*.json"):
                existing.unlink()
            (specs_dir / "BAD-MANY-CARDINALITY-TMP.json").write_text(
                json.dumps(
                    {
                        "id": "BAD-MANY-CARDINALITY-TMP",
                        "kind": "page_view",
                        "name": "Bad Many Cardinality",
                        "owner": "web",
                        "status": "active",
                        "description": "A page view with scalar tests binding.",
                        "file": "frontend/src/pages/home/home-page.ts",
                        "tests": "frontend/tests/component/home-page.test.ts",
                    }
                ),
                encoding="utf-8",
            )

            errors = StringIO()
            with redirect_stderr(errors):
                result = main(["--root", str(root), "validate"])

            self.assertEqual(1, result)
            self.assertIn("must be a list of binding paths", errors.getvalue())

            for existing in specs_dir.glob("*.json"):
                existing.unlink()
            (specs_dir / "MISSING-REQUIRED-BINDING-TMP.json").write_text(
                json.dumps(
                    {
                        "id": "MISSING-REQUIRED-BINDING-TMP",
                        "kind": "page_query",
                        "name": "Missing Required Binding",
                        "owner": "web",
                        "status": "active",
                        "description": "A query whose required implementation file is missing.",
                        "repository_file": "frontend/src/pages/home/missing-query.ts",
                    }
                ),
                encoding="utf-8",
            )

            errors = StringIO()
            with redirect_stderr(errors):
                result = main(["--root", str(root), "validate"])

            self.assertEqual(1, result)
            self.assertIn("GROUNDED-BINDING-009", errors.getvalue())

            for existing in specs_dir.glob("*.json"):
                existing.unlink()
            (specs_dir / "UNSUPPORTED-BINDING-TARGET-TMP.json").write_text(
                json.dumps(
                    {
                        "id": "UNSUPPORTED-BINDING-TARGET-TMP",
                        "kind": "page_view",
                        "name": "Unsupported Binding Target",
                        "owner": "web",
                        "status": "active",
                        "description": "A page view with an unsupported binding target.",
                        "file": "frontend/src/pages/home/home-page.ts",
                        "bindings": [
                            {
                                "role": "implementation",
                                "target": {
                                    "kind": "url",
                                    "url": "https://example.invalid/home",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            errors = StringIO()
            with redirect_stderr(errors):
                result = main(["--root", str(root), "validate"])

            self.assertEqual(1, result)
            self.assertIn("GROUNDED-BINDING-006", errors.getvalue())

    def test_binding_validation_rejects_malformed_mapping_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            registry_path = root / ".grounded/registry/spec-types.json"
            type_registry = json.loads(registry_path.read_text(encoding="utf-8"))
            type_registry["broken_bindable"] = {
                "extends": "knowledge_unit",
                "capabilities": ["bindable"],
                "binding_field_mappings": ["file"],
                "schema": {
                    "type": "object",
                    "required": [
                        "id",
                        "name",
                        "owner",
                        "status",
                        "description",
                    ],
                    "properties": {
                        "type": {"const": "broken_bindable"},
                        "kind": {"const": "broken_bindable"},
                    },
                    "additionalProperties": True,
                },
                "required": [
                    "id",
                    "name",
                    "owner",
                    "status",
                    "description",
                ],
                "search_fields": ["id", "name", "description"],
                "reference_fields": [],
            }
            registry_path.write_text(
                json.dumps(type_registry, indent=2), encoding="utf-8"
            )

            errors = StringIO()
            with redirect_stderr(errors):
                result = main(["--root", str(root), "validate"])

            self.assertEqual(1, result)
            self.assertIn("GROUNDED-BINDING-005", errors.getvalue())
            self.assertIn(
                "binding_field_mappings[0] must be an object", errors.getvalue()
            )

    def test_context_omission_policy_distinguishes_unsupported_target_kind(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._install_bindable_fixture_types(root)
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            spec_path = specs_dir / "UNSUPPORTED-BINDING-TARGET-TMP.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "id": "UNSUPPORTED-BINDING-TARGET-TMP",
                        "kind": "page_view",
                        "name": "Unsupported Binding Target",
                        "owner": "web",
                        "status": "active",
                        "description": "A page view with an unsupported binding target.",
                        "file": "frontend/src/pages/home/home-page.ts",
                        "bindings": [
                            {
                                "role": "implementation",
                                "target": {
                                    "kind": "url",
                                    "url": "https://example.invalid/home",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            registry = load_registry(load_config(root))
            spec = registry.get("UNSUPPORTED-BINDING-TARGET-TMP")
            self.assertIsNotNone(spec)
            result = bindings_for_spec(
                spec, registry.type_definition_for(spec), project_root=root
            )

            self.assertEqual("url", result.bindings[0].target.kind)
            self.assertIsNone(result.bindings[0].target.path)
            self.assertEqual(
                ["GROUNDED-BINDING-006"],
                [issue.code for issue in result.bindings[0].validation_issues],
            )

    def test_optional_missing_binding_is_reported_as_context_omission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self._install_bindable_fixture_types(root)
            (root / "frontend/src/pages/home").mkdir(parents=True)
            (root / "frontend/src/pages/home/home-page.ts").write_text(
                "export class HomePageElement {}\n",
                encoding="utf-8",
            )
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            (specs_dir / "PAGE-VIEW-MISSING-TEST.json").write_text(
                json.dumps(
                    {
                        "id": "PAGE-VIEW-MISSING-TEST",
                        "kind": "page_view",
                        "name": "Home Page View",
                        "owner": "web",
                        "status": "active",
                        "description": "Renders the home page.",
                        "file": "frontend/src/pages/home/home-page.ts",
                        "tests": ["frontend/tests/component/missing.test.ts"],
                    }
                ),
                encoding="utf-8",
            )

            output = StringIO()
            errors = StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "PAGE-VIEW-MISSING-TEST",
                        "--depth",
                        "0",
                        "--include-bindings",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual("", errors.getvalue())
            payload = json.loads(output.getvalue())
            missing_binding = payload["items"][0]["bindings"][1]
            self.assertFalse(missing_binding["binding_included"])
            self.assertEqual("missing_path", missing_binding["omitted_reason"])
            self.assertEqual("warning", missing_binding["validation"]["status"])

            output = StringIO()
            errors = StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                result = main(
                    [
                        "--root",
                        str(root),
                        "context",
                        "PAGE-VIEW-MISSING-TEST",
                        "--depth",
                        "0",
                        "--include-bindings",
                    ]
                )

            self.assertEqual(0, result)
            self.assertIn("GROUNDED-BINDING-009", errors.getvalue())
            self.assertIn(
                "test: `frontend/tests/component/missing.test.ts` "
                "_(warning: missing_path; content not included)_",
                output.getvalue(),
            )

            output = StringIO()
            errors = StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                result = main(
                    [
                        "--root",
                        str(root),
                        "search",
                        "Home Page View",
                    ]
                )

            self.assertEqual(0, result)
            self.assertIn("GROUNDED-BINDING-009", errors.getvalue())

            output = StringIO()
            errors = StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                result = main(
                    [
                        "--root",
                        str(root),
                        "search",
                        "Home Page View",
                        "--json",
                    ]
                )

            self.assertEqual(0, result)
            json.loads(output.getvalue())
            self.assertEqual("", errors.getvalue())

    def test_registry_cli_lists_registry_types_and_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            item_id = "".join(["TODO", "-ITEM-001"])
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            (specs_dir / f"{item_id}.json").write_text(
                json.dumps(
                    {
                        "id": item_id,
                        "kind": "domain_object",
                        "name": "Todo Item",
                        "owner": "todo",
                        "status": "active",
                        "description": "A user-visible task in the todo list.",
                    }
                ),
                encoding="utf-8",
            )

            output = StringIO()
            with redirect_stdout(output):
                result = main(["--root", str(root), "registry", "--json"])

            self.assertEqual(0, result)
            payload = json.loads(output.getvalue())
            registry_unit = next(
                item
                for item in payload["registry_types"]
                if item["type"] == "registry_unit"
            )
            self.assertIsNone(registry_unit["extends"])
            self.assertEqual(["id", "name", "status"], registry_unit["required"])
            self.assertEqual([], registry_unit["reference_fields"])
            spec_ids = {spec["id"] for spec in payload["specs"]}
            self.assertIn(item_id, spec_ids)
            self.assertIn("PROJECT-GAP-001", spec_ids)

            output = StringIO()
            with redirect_stdout(output):
                result = main(["--root", str(root), "registry"])

            self.assertEqual(0, result)
            text = output.getvalue()
            self.assertIn("Grounded registry", text)
            self.assertIn("Registry types", text)
            self.assertIn("Authored specs", text)
            self.assertIn("- registry_unit", text)
            self.assertIn(f"  {item_id} - Todo Item", text)
            self.assertIn("    type: domain_object, owner: todo, status: active", text)

    def test_documented_units_require_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            path = root / ".grounded/specs/examples/TODO-ITEM-001.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "id": "TODO-ITEM-001",
                        "kind": "domain_object",
                        "name": "Todo Item",
                        "owner": "todo",
                        "status": "active",
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)

            self.assertTrue(
                any(
                    issue.code == "GROUNDED-SCHEMA-003"
                    and "description" in issue.message
                    for issue in registry.issues
                )
            )

    def test_rich_text_links_render_and_validate_as_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            item = {
                "id": "TODO-ITEM-001",
                "kind": "domain_object",
                "name": "TodoItem",
                "short_name": "Task",
                "owner": "todo",
                "status": "active",
                "description": "Defines the task target.",
                "fields": [
                    {
                        "name": "title",
                        "type": "string",
                        "required": True,
                        "description": "The title field.",
                    }
                ],
            }
            overview = {
                "id": "TODO-CONCEPT-001",
                "kind": "domain_object",
                "name": "Todo overview",
                "owner": "todo",
                "status": "active",
                "description": (
                    "Links to [[TODO-ITEM-001|Task]], "
                    "[[TODO-ITEM-001#field-todo-item-001-title|title field]], "
                    "[[tag:planned|planned work]], **strong text**, _emphasis_, "
                    "`code`, and <script>escaped</script>."
                ),
            }
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            for spec in (item, overview):
                (specs_dir / f"{spec['id']}.json").write_text(
                    json.dumps(spec), encoding="utf-8"
                )

            config = load_config(root)
            registry = load_registry(config)

            self.assertEqual([], registry.issues)
            self.assertIn(
                "TODO-ITEM-001", registry.by_id["TODO-CONCEPT-001"].references
            )

            render_all(config, registry)

            overview_html = (
                root / ".grounded/generated/docs/units/todo-concept-001.html"
            ).read_text(encoding="utf-8")
            item_html = (
                root / ".grounded/generated/docs/units/todo-item-001.html"
            ).read_text(encoding="utf-8")
            markdown = (root / ".grounded/generated/docs/project-memory.md").read_text(
                encoding="utf-8"
            )

            self.assertIn(
                '<grounded-link type="domain_object" grounded-id="TODO-ITEM-001" label="Task" variant="plain">Task</grounded-link>',
                overview_html,
            )
            self.assertIn(
                '<grounded-link type="domain_object" grounded-id="TODO-ITEM-001" label="title field" fragment="field-todo-item-001-title" variant="plain">title field</grounded-link>',
                overview_html,
            )
            self.assertIn(
                '<grounded-link type="tag" grounded-id="planned" label="planned work" variant="tag">planned work</grounded-link>',
                overview_html,
            )
            self.assertIn("<strong>strong text</strong>", overview_html)
            self.assertIn("<em>emphasis</em>", overview_html)
            self.assertIn("<code>code</code>", overview_html)
            self.assertIn("&lt;script&gt;escaped&lt;/script&gt;", overview_html)
            self.assertIn("Todo overview", item_html)
            self.assertIn("Links to Task, title field, planned work", markdown)

            missing_id = "MISSING" + "-SPEC-001"
            overview["description"] = f"Broken [[{missing_id}]] link."
            (specs_dir / f"{overview['id']}.json").write_text(
                json.dumps(overview), encoding="utf-8"
            )
            broken = load_registry(config)

            self.assertTrue(
                any(
                    issue.code == "GROUNDED-REF-001" and missing_id in issue.message
                    for issue in broken.issues
                )
            )

    def test_validate_flags_unknown_nested_reference_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            registry_path = root / ".grounded/registry/spec-types.json"
            type_registry = json.loads(registry_path.read_text(encoding="utf-8"))
            type_registry["artifact_contract"] = {
                "extends": "knowledge_unit",
                "nested_reference_fields": ["fields.metric_contract"],
                "schema": {
                    "type": "object",
                    "required": ["id", "name", "owner", "status", "description"],
                    "properties": {
                        "kind": {"const": "artifact_contract"},
                        "type": {"const": "artifact_contract"},
                        "fields": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                    },
                    "additionalProperties": True,
                },
            }
            registry_path.write_text(json.dumps(type_registry), encoding="utf-8")

            artifact_id = "PROJECT" + "-ARTIFACT-001"
            missing_metric_id = "PROJECT" + "-METRIC-999"
            artifact = {
                "id": artifact_id,
                "kind": "artifact_contract",
                "name": "Project artifact",
                "owner": "project",
                "status": "active",
                "description": "A contract with field-level metric links.",
                "fields": [
                    {
                        "name": "amount",
                        "type": "Decimal",
                        "metric_contract": missing_metric_id,
                    }
                ],
            }
            artifact_path = root / ".grounded/specs/artifacts" / f"{artifact_id}.json"
            artifact_path.parent.mkdir()
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

            registry = load_registry(load_config(root))

            self.assertTrue(
                any(
                    issue.code == "GROUNDED-REF-001"
                    and "fields.metric_contract" in issue.message
                    and missing_metric_id in issue.message
                    for issue in registry.issues
                )
            )

    def test_typed_tags_render_and_validate_against_tag_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            registry_path = root / ".grounded/registry/spec-types.json"
            type_registry = json.loads(registry_path.read_text(encoding="utf-8"))
            type_registry["tag_types"] = {
                "EntityType": {
                    "values": ["BusinessEntity", "CodeEntity"],
                    "description": "Classifies specs by entity role.",
                }
            }
            registry_path.write_text(json.dumps(type_registry), encoding="utf-8")

            item = {
                "id": "TODO-ITEM-001",
                "kind": "domain_object",
                "name": "TodoItem",
                "owner": "todo",
                "status": "active",
                "description": "A business entity for a tracked todo.",
                "tags": [{"type": "EntityType", "value": "BusinessEntity"}],
                "fields": [
                    {
                        "name": "component",
                        "type": "string",
                        "description": "Related implementation component.",
                        "tags": [{"type": "EntityType", "value": "CodeEntity"}],
                    }
                ],
            }
            item_path = root / ".grounded/specs/examples/TODO-ITEM-001.json"
            item_path.parent.mkdir(exist_ok=True)
            item_path.write_text(json.dumps(item), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            self.assertEqual([], registry.issues)
            item_html = (
                root / ".grounded/generated/docs/units/todo-item-001.html"
            ).read_text(encoding="utf-8")
            tag_html = (
                root / ".grounded/generated/docs/tags/entitytype-businessentity.html"
            ).read_text(encoding="utf-8")

            self.assertIn(
                "EntityType:BusinessEntity", registry.by_id["TODO-ITEM-001"].tags
            )
            self.assertIn(
                '<grounded-link type="tag" grounded-id="EntityType:BusinessEntity" label="EntityType:BusinessEntity" variant="tag">EntityType:BusinessEntity</grounded-link>',
                item_html,
            )
            self.assertIn("<grounded-tag-page>", tag_html)
            self.assertIn("TodoItem", tag_html)

            item["tags"] = [{"type": "EntityType", "value": "OtherEntity"}]
            item_path.write_text(json.dumps(item), encoding="utf-8")
            broken = load_registry(config)

            self.assertTrue(
                any(
                    issue.code == "GROUNDED-TAG-002" and "OtherEntity" in issue.message
                    for issue in broken.issues
                )
            )

    def test_reference_tag_constraints_require_target_typed_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            registry_path = root / ".grounded/registry/spec-types.json"
            type_registry = json.loads(registry_path.read_text(encoding="utf-8"))
            type_registry["tag_types"] = {
                "EntityType": {"values": ["BusinessEntity", "CodeEntity"]}
            }
            type_registry["workplan_requirement"] = {
                "extends": "knowledge_unit",
                "reference_fields": ["related_entities"],
                "reference_tag_constraints": {
                    "related_entities": {
                        "type": "EntityType",
                        "value": "BusinessEntity",
                    }
                },
                "schema": {
                    "type": "object",
                    "required": [
                        "id",
                        "name",
                        "owner",
                        "status",
                        "description",
                        "related_entities",
                    ],
                    "properties": {
                        "kind": {"const": "workplan_requirement"},
                        "type": {"const": "workplan_requirement"},
                        "related_entities": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "additionalProperties": True,
                },
            }
            registry_path.write_text(json.dumps(type_registry), encoding="utf-8")

            item_id = "TODO" + "-ITEM-001"
            code_id = "TODO" + "-CODE-001"
            requirement_id = "TODO" + "-REQ-001"
            business_entity = {
                "id": item_id,
                "kind": "domain_object",
                "name": "TodoItem",
                "owner": "todo",
                "status": "active",
                "description": "A business entity.",
                "tags": [{"type": "EntityType", "value": "BusinessEntity"}],
            }
            code_entity = {
                "id": code_id,
                "kind": "domain_object",
                "name": "TodoRepository",
                "owner": "todo",
                "status": "active",
                "description": "A code entity.",
                "tags": [{"type": "EntityType", "value": "CodeEntity"}],
            }
            requirement = {
                "id": requirement_id,
                "kind": "workplan_requirement",
                "name": "Todo planning requirement",
                "owner": "todo",
                "status": "active",
                "description": "Requires references to business entities.",
                "related_entities": [item_id, code_id],
            }
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(exist_ok=True)
            for spec in (business_entity, code_entity, requirement):
                (specs_dir / f"{spec['id']}.json").write_text(
                    json.dumps(spec), encoding="utf-8"
                )

            registry = load_registry(load_config(root))

            self.assertTrue(
                any(
                    issue.code == "GROUNDED-REF-005"
                    and code_id in issue.message
                    and "EntityType:BusinessEntity" in issue.message
                    for issue in registry.issues
                )
            )
            self.assertFalse(
                any(
                    issue.code == "GROUNDED-REF-005" and item_id in issue.message
                    for issue in registry.issues
                )
            )

    def test_default_css_is_bundled_with_package(self) -> None:
        css = default_css()

        self.assertIn(":root", css)
        self.assertIn("--color-", css)
        self.assertIn("--color-brand-primary: #5645d4;", css)

    def test_render_focuses_domain_units_and_keeps_background_separate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            todo = {
                "id": "TODO-LIST-001",
                "kind": "domain_object",
                "name": "TodoItem",
                "owner": "todo",
                "status": "active",
                "summary": "A task that can be tracked to completion.",
            }
            path = root / ".grounded/specs/examples/TODO-LIST-001.json"
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(todo), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            html = (root / ".grounded/generated/docs/index.html").read_text(
                encoding="utf-8"
            )
            visible_html = html.split('<grounded-main slot="main"', 1)[1].split(
                "</grounded-main>", 1
            )[0]
            background = (
                root / ".grounded/generated/docs/grounded-background.html"
            ).read_text(encoding="utf-8")
            search = json.loads(
                (root / ".grounded/generated/docs/search-index.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertIn("TodoItem", visible_html)
            self.assertIn("grounded-background.html", visible_html)
            self.assertNotIn(
                "Project-specific fact shapes belong in the type registry",
                visible_html,
            )
            self.assertIn(
                "Project-specific fact shapes belong in the type registry",
                background,
            )
            self.assertEqual(["TODO-LIST-001"], [item["id"] for item in search])
            self.assertIn("grounded-search-index", html)
            self.assertNotIn("fetch(", html)
            self.assertIn("<grounded-search", background)
            self.assertIn("grounded-search-index", background)

    def test_unit_page_renders_fields_before_collapsed_raw_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            invariant = {
                "id": "TODO-CONCEPT-001",
                "kind": "concept",
                "concept_role": "invariant",
                "name": "TodoItem belongs to one list",
                "short_name": "One list",
                "owner": "todo",
                "references": ["TODO-ITEM-001"],
                "status": "active",
                "summary": "A TodoItem belongs to exactly one TodoList.",
            }
            status_value = {
                "id": "TODO-STATUS-001",
                "kind": "lifecycle_value",
                "name": "Open",
                "short_name": "Open",
                "owner": "todo",
                "references": ["TODO-LIFECYCLE-001"],
                "status": "active",
                "summary": "Open means work has not started yet.",
            }
            status_type = {
                "id": "TODO-LIFECYCLE-001",
                "kind": "lifecycle_type",
                "name": "TodoStatus",
                "short_name": "Status",
                "owner": "todo",
                "references": ["TODO-STATUS-001"],
                "status": "active",
                "definition": "The lifecycle vocabulary for a todo item.",
            }
            string_type = {
                "id": "TODO-DATA-TYPE-001",
                "kind": "data_type",
                "name": "string",
                "short_name": "Text",
                "owner": "todo",
                "references": ["TODO-ITEM-001"],
                "status": "active",
                "definition": "A textual value.",
            }
            build_decision = {
                "id": "GROUNDED-DECISION-019",
                "kind": "decision",
                "name": "Use TodoItem for renderer example",
                "owner": "grounded",
                "references": ["TODO-ITEM-001"],
                "status": "active",
                "decision": "The example uses TodoItem to exercise unit rendering.",
            }
            todo = {
                "id": "TODO-ITEM-001",
                "kind": "domain_object",
                "name": "TodoItem",
                "short_name": "Task",
                "owner": "todo",
                "status": "active",
                "definition": "A task that can be tracked to completion.",
                "fields": [
                    {
                        "name": "title",
                        "type": "string",
                        "required": True,
                        "description": "Short human-readable task text.",
                    },
                    {
                        "name": "status",
                        "type": "TodoStatus",
                        "required": True,
                        "description": "Current lifecycle state of the item.",
                        "tags": ["planned"],
                    },
                    {
                        "name": "related_items",
                        "type": "list[TodoItem] | None",
                        "required": False,
                        "description": "Related tasks.",
                        "references": ["TODO-CONCEPT-001"],
                    },
                ],
                "references": [],
            }
            invariant_path = root / ".grounded/specs/examples/TODO-CONCEPT-001.json"
            invariant_path.parent.mkdir(exist_ok=True)
            invariant_path.write_text(json.dumps(invariant), encoding="utf-8")
            status_path = root / ".grounded/specs/examples/TODO-STATUS-001.json"
            status_path.write_text(json.dumps(status_value), encoding="utf-8")
            status_type_path = root / ".grounded/specs/examples/TODO-LIFECYCLE-001.json"
            status_type_path.write_text(json.dumps(status_type), encoding="utf-8")
            string_type_path = root / ".grounded/specs/examples/TODO-DATA-TYPE-001.json"
            string_type_path.write_text(json.dumps(string_type), encoding="utf-8")
            decision_path = root / ".grounded/specs/examples/GROUNDED-DECISION-019.json"
            decision_path.write_text(json.dumps(build_decision), encoding="utf-8")
            path = root / ".grounded/specs/examples/TODO-ITEM-001.json"
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(todo), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            html = (
                root / ".grounded/generated/docs/units/todo-item-001.html"
            ).read_text(encoding="utf-8")
            index_html = (root / ".grounded/generated/docs/index.html").read_text(
                encoding="utf-8"
            )
            lifecycle_html = (
                root / ".grounded/generated/docs/units/todo-lifecycle-001.html"
            ).read_text(encoding="utf-8")

            self.assertIn("field-table", html)
            self.assertIn('id="field-todo-item-001-title"', html)
            self.assertIn("Short human-readable task text.", html)
            self.assertIn("Current lifecycle state of the item.", html)
            self.assertIn("field-required", html)
            self.assertIn(
                '<grounded-link type="data_type" grounded-id="TODO-DATA-TYPE-001" label="Text" variant="field-type">Text</grounded-link>',
                html,
            )
            self.assertIn(
                '<grounded-link type="lifecycle_type" grounded-id="TODO-LIFECYCLE-001" label="Status" variant="field-type">Status</grounded-link>',
                html,
            )
            self.assertIn("<span>Tags:</span>", html)
            self.assertIn(
                '<grounded-link type="tag" grounded-id="planned" label="planned" variant="tag">planned</grounded-link>',
                html,
            )
            self.assertIn(
                'list[<grounded-link type="domain_object" grounded-id="TODO-ITEM-001" label="Task" variant="field-type">Task</grounded-link>]',
                html,
            )
            self.assertIn("<span>References:</span>", html)
            self.assertIn(
                '<grounded-link type="concept" grounded-id="TODO-CONCEPT-001" label="One list" variant="plain">One list</grounded-link>',
                html,
            )
            self.assertIn("Invariants", html)
            self.assertIn("One list", html)
            self.assertIn("A TodoItem belongs to exactly one TodoList.", html)
            self.assertNotIn("Status Values", html)
            self.assertIn("Status Values", lifecycle_html)
            self.assertIn(
                '<grounded-link type="lifecycle_value" grounded-id="TODO-STATUS-001" label="Open" variant="plain">Open</grounded-link>',
                lifecycle_html,
            )
            self.assertIn("Open means work has not started yet.", lifecycle_html)
            self.assertNotIn("Related Concepts", html)
            self.assertIn(
                '<grounded-link type="domain_object" grounded-id="TODO-ITEM-001" label="Task" variant="nav">Task</grounded-link>',
                html,
            )
            self.assertIn(
                '<grounded-link type="concept" grounded-id="TODO-CONCEPT-001" label="One list" variant="plain">One list</grounded-link>',
                html,
            )
            self.assertEqual(
                '<grounded-link type="domain_object" grounded-id="TODO-ITEM-001" label="Summary" fragment="field-todo-item-001-summary" variant="plain">Summary</grounded-link>',
                grounded_link(
                    "domain_object",
                    "TODO-ITEM-001",
                    "Summary",
                    "plain",
                    "field-todo-item-001-summary",
                ),
            )
            visible_links = html.split('<grounded-links-panel slot="links">', 1)[
                1
            ].split("</grounded-links-panel>", 1)[0]
            self.assertIn("One list", visible_links)
            self.assertNotIn("Use TodoItem for renderer example", visible_links)
            self.assertIn('<details class="raw-unit">', html)
            self.assertIn("<summary>Raw JSON</summary>", html)
            self.assertIn("<grounded-search", html)
            self.assertIn("<grounded-nav-group open>", html)
            self.assertNotIn("<grounded-nav-group open>", index_html)
            self.assertIn("grounded-search-index", html)
            self.assertIn('href="../style.css"', html)
            self.assertIn('<grounded-doc-header slot="hero">', html)
            self.assertIn(
                '<grounded-copy-id slot="actions" value="TODO-ITEM-001">', html
            )
            self.assertNotIn("owner:", html.split('<grounded-main slot="main"', 1)[1])
            self.assertIn('<span slot="eyebrow">Domain Object</span>', html)
            self.assertLess(
                html.index("field-table"),
                html.index('<details class="raw-unit">'),
            )

            component_js = (
                root / ".grounded/generated/docs/grounded-link.js"
            ).read_text(encoding="utf-8")
            self.assertIn("class GroundedDocHeader extends LitElement", component_js)
            self.assertIn("class GroundedSection extends LitElement", component_js)
            self.assertIn("class GroundedPillLinkList extends LitElement", component_js)
            self.assertIn("class GroundedDetailRow extends LitElement", component_js)
            self.assertIn("class GroundedThemeToggle extends LitElement", component_js)
            self.assertIn("aria-expanded", component_js)
            self.assertIn("this.open = !this.open", component_js)
            self.assertIn(":host([open]) .items { display: block; }", component_js)
            self.assertIn("tooltipFor(target, label)", component_js)
            self.assertIn("aria-description=${tooltip || nothing}", component_js)
            self.assertIn(
                "aria-describedby=${tooltip ? tooltipId : nothing}", component_js
            )
            self.assertIn("appendTooltipRichText(tooltip, text)", component_js)
            self.assertIn("document.createElement('a')", component_js)
            self.assertIn("link.href = `${target.href}${fragment}`", component_js)
            self.assertIn("document.body.appendChild(tooltip)", component_js)
            self.assertIn("pointerEvents: 'auto'", component_js)
            self.assertIn("scheduleHideHoistedTooltip", component_js)
            self.assertIn("position: 'fixed'", component_js)
            self.assertIn("background: '#ffffff'", component_js)
            self.assertIn("border: '1px solid #000000'", component_js)
            self.assertIn(
                "boxShadow: '0 0.375rem 1rem rgba(0, 0, 0, 0.16)'", component_js
            )
            self.assertIn("target.summary", component_js)
            self.assertIn("define('grounded-theme-toggle'", component_js)
            self.assertIn("grounded-theme", component_js)
            self.assertIn("var(--color-text-primary)", component_js)
            self.assertIn("var(--space-md)", component_js)

    def test_enum_page_renders_closed_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            enum_id = "".join(["TODO", "-PRIORITY-001"])
            enum_spec = {
                "id": enum_id,
                "kind": "enum",
                "name": "TaskPriority",
                "short_name": "Priority",
                "owner": "todo",
                "status": "active",
                "definition": "The closed set of priority values for a task.",
                "values": ["low", "medium", "high"],
            }
            path = root / ".grounded/specs/examples" / f"{enum_id}.json"
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(enum_spec), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            html = (
                root / ".grounded/generated/docs/units/todo-priority-001.html"
            ).read_text(encoding="utf-8")

            self.assertIn("<grounded-enum-page>", html)
            self.assertIn(
                "<grounded-section-heading>Values</grounded-section-heading>", html
            )
            self.assertIn('<span class="tag t-type field-value">low</span>', html)
            self.assertIn('<span class="tag t-type field-value">medium</span>', html)
            self.assertIn('<span class="tag t-type field-value">high</span>', html)
            self.assertIn("The closed set of priority values for a task.", html)

    def test_tag_pages_render_and_group_members_by_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            enum_id = "".join(["TODO", "-PRIORITY-001"])
            deprecated = {
                "id": "TODO-ITEM-001",
                "kind": "domain_object",
                "name": "TodoItem",
                "short_name": "Task",
                "owner": "todo",
                "status": "active",
                "summary": "A tracked task.",
                "tags": ["deprecated", "planned"],
                "fields": [
                    {
                        "name": "legacy_code",
                        "type": "string",
                        "required": False,
                        "description": "Legacy identifier still carried for compatibility.",
                        "tags": ["deprecated"],
                    }
                ],
            }
            planned_enum = {
                "id": enum_id,
                "kind": "enum",
                "name": "TaskPriority",
                "short_name": "Priority",
                "owner": "todo",
                "status": "active",
                "definition": "Priority values for tasks.",
                "values": ["low", "high"],
                "tags": ["planned"],
            }
            item_path = root / ".grounded/specs/examples/TODO-ITEM-001.json"
            item_path.parent.mkdir(exist_ok=True)
            item_path.write_text(json.dumps(deprecated), encoding="utf-8")
            enum_path = root / ".grounded/specs/examples" / f"{enum_id}.json"
            enum_path.write_text(json.dumps(planned_enum), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            item_html = (
                root / ".grounded/generated/docs/units/todo-item-001.html"
            ).read_text(encoding="utf-8")
            tag_html = (
                root / ".grounded/generated/docs/tags/deprecated.html"
            ).read_text(encoding="utf-8")
            planned_html = (
                root / ".grounded/generated/docs/tags/planned.html"
            ).read_text(encoding="utf-8")

            self.assertIn("grounded-tag-index", item_html)
            self.assertIn("grounded-compact-list", tag_html)
            self.assertIn("grounded-compact-item", tag_html)
            self.assertIn(
                '<grounded-link type="tag" grounded-id="deprecated" label="deprecated" variant="tag">deprecated</grounded-link>',
                item_html,
            )
            self.assertIn(
                '<grounded-link type="tag" grounded-id="planned" label="planned" variant="tag">planned</grounded-link>',
                item_html,
            )
            self.assertIn("<grounded-tag-page>", tag_html)
            self.assertIn('<span slot="title">deprecated</span>', tag_html)
            self.assertIn(
                "<grounded-section-heading divider>Domain</grounded-section-heading>",
                tag_html,
            )
            self.assertIn("Task", tag_html)
            self.assertIn("Task.legacy_code", tag_html)
            self.assertIn(
                '<grounded-link type="domain_object" grounded-id="TODO-ITEM-001" label="Task.legacy_code" fragment="field-todo-item-001-legacy-code" variant="plain">Task.legacy_code</grounded-link>',
                tag_html,
            )
            self.assertIn(
                "<grounded-section-heading divider>Domain</grounded-section-heading>",
                planned_html,
            )
            self.assertIn(
                "<grounded-section-heading divider>Enums</grounded-section-heading>",
                planned_html,
            )
            self.assertIn("Priority", planned_html)

    def test_slice_pages_render_scoped_members_with_metadata_and_overrides(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            templates_dir = root / ".grounded/renderers/templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "custom-slice.html.j2").write_text(
                """{% extends "slice-index.html.j2" %}
{% block content %}
<grounded-index-page>
<grounded-page-hero>
  <span slot="eyebrow">Custom Slice</span>
  <span slot="title">{{ slice.data.name }}</span>
  <span slot="description">{{ slice_description }}</span>
</grounded-page-hero>
<p class="custom-marker">{{ slice_members | length }} scoped members</p>
{{ super() }}
</grounded-index-page>
{% endblock %}
""",
                encoding="utf-8",
            )
            (root / "slice.css").write_text(
                ".custom-marker { color: rebeccapurple; }\n", encoding="utf-8"
            )
            todo_id = "TODO" + "-ITEM-001"
            status_id = "TODO" + "-STATUS-001"
            unrelated_id = "UNRELATED" + "-ITEM-001"
            slice_id = "TODO" + "-SLICE-001"
            todo = {
                "id": todo_id,
                "kind": "domain_object",
                "name": "TodoItem",
                "short_name": "Task",
                "owner": "todo",
                "status": "active",
                "description": "Defines the todo item used by the slice rendering test.",
                "summary": "A tracked task.",
            }
            status = {
                "id": status_id,
                "kind": "enum",
                "name": "TodoStatus",
                "owner": "todo",
                "status": "active",
                "description": "Defines the todo status values used by the slice rendering test.",
                "values": ["open", "done"],
            }
            unrelated = {
                "id": unrelated_id,
                "kind": "domain_object",
                "name": "UnrelatedThing",
                "owner": "other",
                "status": "active",
                "description": "Defines an unrelated item that should stay out of the slice.",
                "summary": "Noise outside the slice.",
            }
            slice_spec = {
                "id": slice_id,
                "kind": "slice",
                "name": "Todo core",
                "owner": "todo",
                "status": "active",
                "description": "The minimal todo model.",
                "slug": "todo-core",
                "members": [todo_id, status_id],
                "index_template": "custom-slice.html.j2",
                "style_path": "slice.css",
            }
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            for spec in (todo, status, unrelated, slice_spec):
                (specs_dir / f"{spec['id']}.json").write_text(
                    json.dumps(spec), encoding="utf-8"
                )

            config = load_config(root)
            registry = load_registry(config)

            self.assertEqual([], registry.issues)
            render_all(config, registry)

            slice_html = (
                root / ".grounded/generated/docs/slices/todo-core/index.html"
            ).read_text(encoding="utf-8")
            slice_css = root / ".grounded/generated/docs/slices/todo-core/slice.css"
            search = slice_html.split(
                '<script type="application/json" id="grounded-search-index">',
                1,
            )[1].split("</script>", 1)[0]

            self.assertTrue(slice_css.exists())
            self.assertIn('href="../../style.css"', slice_html)
            self.assertIn('href="slice.css"', slice_html)
            self.assertIn("Custom Slice", slice_html)
            self.assertIn("The minimal todo model.", slice_html)
            self.assertIn("2 scoped members", slice_html)
            self.assertIn("Task", slice_html)
            self.assertIn("TodoStatus", slice_html)
            self.assertNotIn("UnrelatedThing", slice_html)
            self.assertIn(todo_id, search)
            self.assertNotIn(unrelated_id, search)

            obsolete = root / ".grounded/generated/docs/slices/old-slice/index.html"
            obsolete.parent.mkdir(parents=True)
            obsolete.write_text("stale", encoding="utf-8")

            self.assertIn(
                ".grounded/generated/docs/slices/old-slice/index.html",
                render_all(config, registry, check=True),
            )

            render_all(config, registry)

            self.assertFalse(obsolete.exists())

    def test_audit_requires_test_coverage_for_configured_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            item = {
                "id": "TODO-ITEM-001",
                "kind": "domain_object",
                "name": "Coverage Item",
                "owner": "todo",
                "status": "active",
                "description": "A domain object without test coverage.",
            }
            specs_dir = root / ".grounded/specs/examples"
            specs_dir.mkdir(parents=True)
            (specs_dir / f"{item['id']}.json").write_text(
                json.dumps(item), encoding="utf-8"
            )
            config_path = root / "grounded.yml"
            config_path.write_text(
                config_path.read_text(encoding="utf-8").replace(
                    "required_test_kinds:", "required_test_kinds: domain_object"
                ),
                encoding="utf-8",
            )

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)
            issues = audit(config, registry)

            self.assertTrue(
                any(issue.code == "GROUNDED-COVERAGE-001" for issue in issues)
            )

    def test_audit_flags_unknown_grounded_id_in_declared_artifact_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            (root / "docs").mkdir()
            missing_id = "MISSING" + "-RULE-999"
            (root / "docs/spec.md").write_text(
                f"This references {missing_id}.", encoding="utf-8"
            )

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)
            issues = audit(config, registry)

            self.assertTrue(any(issue.code == "GROUNDED-REF-004" for issue in issues))

    def test_validate_flags_unknown_kind_not_declared_in_type_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            rogue_id = "PROJECT" + "-ROGUE-001"
            rogue = {
                "id": rogue_id,
                "kind": "rogue_kind",
                "name": "Rogue kind",
                "owner": "project",
                "status": "active",
            }
            path = root / ".grounded/specs/rogue" / f"{rogue_id}.json"
            path.parent.mkdir()
            path.write_text(json.dumps(rogue), encoding="utf-8")

            registry = load_registry(load_config(root))

            self.assertTrue(
                any(issue.code == "GROUNDED-KIND-001" for issue in registry.issues)
            )

    def test_domain_object_core_schema_is_semantically_thin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            path = root / ".grounded/specs/examples/TODO-ITEM-001.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "id": "TODO-ITEM-001",
                        "kind": "domain_object",
                        "name": "Todo Item",
                        "owner": "todo",
                        "status": "active",
                        "description": "A placeholder domain object.",
                        "fields": [{"name": "id", "type": "string", "required": "yes"}],
                    }
                ),
                encoding="utf-8",
            )

            registry = load_registry(load_config(root))

            self.assertFalse(
                any(
                    issue.code.startswith("GROUNDED-DOMAIN")
                    for issue in registry.issues
                )
            )

    def test_verify_runs_type_configured_project_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            verification = (
                root / ".grounded/specs/verifications/PROJECT-VERIFY-001.json"
            )
            data = json.loads(verification.read_text(encoding="utf-8"))
            data["command"] = "python -c 'raise SystemExit(3)'"
            verification.write_text(json.dumps(data), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            issues = verify(config, registry)

            self.assertTrue(
                any(issue.code == "GROUNDED-VERIFY-001" for issue in issues)
            )


if __name__ == "__main__":
    unittest.main()
