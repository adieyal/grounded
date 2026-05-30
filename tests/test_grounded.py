from __future__ import annotations

import json
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import grounded.audit as audit_module
from grounded.audit import audit
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
from grounded.verify import verify


class GroundedTests(unittest.TestCase):
    def test_package_version_is_synchronized(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual("1.0.0", pyproject["project"]["version"])
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

    def test_audit_requires_markdown_docs_to_be_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
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
