from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lattice.audit import audit
from lattice.bootstrap import AGENTS_MARKER_START, init_project
from lattice.config import load_config
from lattice.registry import default_type_registry_json, load_registry
from lattice.render import default_css, lattice_link, render_all
from lattice.verify import verify


class LatticeTests(unittest.TestCase):
    def test_init_creates_specs_and_skill_without_agents_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = init_project(root)

            self.assertIn(root / "lattice.yml", created)
            self.assertTrue(
                (root / ".lattice/specs/glossary/PROJECT-DOMAIN-001.json").exists()
            )
            self.assertTrue(
                (root / ".lattice/specs/schema_gaps/PROJECT-GAP-001.json").exists()
            )
            self.assertTrue(
                (root / ".lattice/specs/verifications/PROJECT-VERIFY-001.json").exists()
            )
            self.assertTrue((root / ".lattice/registry/spec-types.json").exists())
            type_registry = json.loads(
                (root / ".lattice/registry/spec-types.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                ["domain_object", "enum", "knowledge_unit", "schema_gap", "verification"],
                sorted(type_registry),
            )
            self.assertNotIn("business_entity", type_registry)
            self.assertIn(
                "specs_dir: .lattice/specs",
                (root / "lattice.yml").read_text(encoding="utf-8"),
            )
            self.assertTrue((root / ".lattice/schemas/spec.schema.json").exists())
            self.assertTrue((root / ".lattice/templates/domain_object.json").exists())
            self.assertTrue((root / ".lattice/templates/schema_gap.json").exists())
            self.assertFalse(
                (root / ".lattice/renderers/templates/unit.html.j2").exists()
            )
            self.assertTrue((root / "skills/lattice-project-memory/SKILL.md").exists())
            self.assertFalse((root / "AGENTS.md").exists())

    def test_init_can_update_agents_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = init_project(root, update_agents=True)

            self.assertIn(root / "AGENTS.md", created)
            self.assertIn(
                AGENTS_MARKER_START, (root / "AGENTS.md").read_text(encoding="utf-8")
            )

    def test_init_allows_custom_lattice_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root, lattice_dir="docs/memory")
            config = load_config(root)

            self.assertTrue((root / "docs/memory/specs").exists())
            self.assertEqual(root / "docs/memory/specs", config.specs_dir)
            self.assertIn(
                "specs_dir: docs/memory/specs",
                (root / "lattice.yml").read_text(encoding="utf-8"),
            )

    def test_validate_and_render_check_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            config = load_config(root)
            registry = load_registry(config)

            self.assertEqual([], registry.issues)
            self.assertNotEqual([], render_all(config, registry, check=True))
            render_all(config, registry)
            self.assertEqual([], render_all(config, registry, check=True))
            html = (root / ".lattice/generated/docs/project-memory.html").read_text(
                encoding="utf-8"
            )
            css = (root / ".lattice/generated/docs/style.css").read_text(
                encoding="utf-8"
            )
            search = (root / ".lattice/generated/docs/search-index.json").read_text(
                encoding="utf-8"
            )
            self.assertIn("<lattice-main", html)
            self.assertIn("<lattice-unit-card", html)
            self.assertIn("<lattice-search", html)
            self.assertIn("lattice-registry", html)
            self.assertIn("lattice-link.js", html)
            self.assertIn("Canonical project fact", html)
            self.assertIn("Schema Gap", html)
            self.assertNotIn("Todo system", html)
            self.assertIn('href="style.css"', html)
            self.assertIn(":root", css)
            self.assertIn("Canonical project fact", search)

    def test_todo_example_is_a_separate_lattice_project(self) -> None:
        root = Path(__file__).resolve().parents[1]
        distribution_todo_specs = list((root / "lattice/specs").rglob("TODO-*.json"))
        example_root = root / "examples/todo"
        example_config = load_config(example_root)
        example_registry = load_registry(example_config)

        self.assertEqual([], distribution_todo_specs)
        self.assertTrue((example_root / "lattice.yml").exists())
        self.assertTrue((example_root / "lattice/specs/TODO-ITEM-001.json").exists())
        self.assertEqual([], example_registry.issues)
        self.assertIn("TODO-ITEM-001", example_registry.by_id)
        self.assertEqual(
            example_root / "lattice/registry/spec-types.json",
            example_config.type_registry_path,
        )

    def test_default_type_registry_is_core_only(self) -> None:
        type_registry = json.loads(default_type_registry_json())

        self.assertEqual(
            ["domain_object", "enum", "knowledge_unit", "schema_gap", "verification"],
            sorted(type_registry),
        )
        self.assertNotIn("business_entity", type_registry)
        self.assertNotIn("lifecycle_type", type_registry)

    def test_default_css_is_bundled_with_package(self) -> None:
        css = default_css()

        self.assertIn(":root", css)
        self.assertIn("--color-", css)

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
            path = root / ".lattice/specs/examples/TODO-LIST-001.json"
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(todo), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            html = (root / ".lattice/generated/docs/project-memory.html").read_text(
                encoding="utf-8"
            )
            visible_html = html.split('<lattice-main slot="main"', 1)[1].split(
                "</lattice-main>", 1
            )[0]
            background = (
                root / ".lattice/generated/docs/lattice-background.html"
            ).read_text(encoding="utf-8")
            search = json.loads(
                (root / ".lattice/generated/docs/search-index.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertIn("TodoItem", visible_html)
            self.assertIn("lattice-background.html", visible_html)
            self.assertNotIn("Canonical project fact", visible_html)
            self.assertIn("Canonical project fact", background)
            self.assertEqual(["TODO-LIST-001"], [item["id"] for item in search])
            self.assertIn("lattice-search-index", html)
            self.assertNotIn("fetch(", html)
            self.assertIn("<lattice-search", background)
            self.assertIn("lattice-search-index", background)

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
                "id": "LATTICE-DECISION-019",
                "kind": "decision",
                "name": "Use TodoItem for renderer example",
                "owner": "lattice",
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
                    },
                ],
                "references": [],
            }
            invariant_path = root / ".lattice/specs/examples/TODO-CONCEPT-001.json"
            invariant_path.parent.mkdir(exist_ok=True)
            invariant_path.write_text(json.dumps(invariant), encoding="utf-8")
            status_path = root / ".lattice/specs/examples/TODO-STATUS-001.json"
            status_path.write_text(json.dumps(status_value), encoding="utf-8")
            status_type_path = root / ".lattice/specs/examples/TODO-LIFECYCLE-001.json"
            status_type_path.write_text(json.dumps(status_type), encoding="utf-8")
            string_type_path = root / ".lattice/specs/examples/TODO-DATA-TYPE-001.json"
            string_type_path.write_text(json.dumps(string_type), encoding="utf-8")
            decision_path = root / ".lattice/specs/examples/LATTICE-DECISION-019.json"
            decision_path.write_text(json.dumps(build_decision), encoding="utf-8")
            path = root / ".lattice/specs/examples/TODO-ITEM-001.json"
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(todo), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)

            html = (
                root / ".lattice/generated/docs/units/todo-item-001.html"
            ).read_text(encoding="utf-8")
            lifecycle_html = (
                root / ".lattice/generated/docs/units/todo-lifecycle-001.html"
            ).read_text(encoding="utf-8")

            self.assertIn("field-table", html)
            self.assertIn('id="field-todo-item-001-title"', html)
            self.assertIn("Short human-readable task text.", html)
            self.assertIn("Current lifecycle state of the item.", html)
            self.assertIn("field-required", html)
            self.assertIn(
                '<lattice-link type="data_type" lattice-id="TODO-DATA-TYPE-001" label="Text" variant="field-type">Text</lattice-link>',
                html,
            )
            self.assertIn(
                '<lattice-link type="lifecycle_type" lattice-id="TODO-LIFECYCLE-001" label="Status" variant="field-type">Status</lattice-link>',
                html,
            )
            self.assertIn("Invariants", html)
            self.assertIn("One list", html)
            self.assertIn("A TodoItem belongs to exactly one TodoList.", html)
            self.assertNotIn("Status Values", html)
            self.assertIn("Status Values", lifecycle_html)
            self.assertIn(
                '<lattice-link type="lifecycle_value" lattice-id="TODO-STATUS-001" label="Open" variant="plain">Open</lattice-link>',
                lifecycle_html,
            )
            self.assertIn("Open means work has not started yet.", lifecycle_html)
            self.assertNotIn("Related Concepts", html)
            self.assertIn(
                '<lattice-link type="domain_object" lattice-id="TODO-ITEM-001" label="Task" variant="nav">Task</lattice-link>',
                html,
            )
            self.assertIn(
                '<lattice-link type="concept" lattice-id="TODO-CONCEPT-001" label="One list" variant="plain">One list</lattice-link>',
                html,
            )
            self.assertEqual(
                '<lattice-link type="domain_object" lattice-id="TODO-ITEM-001" label="Summary" fragment="field-todo-item-001-summary" variant="plain">Summary</lattice-link>',
                lattice_link(
                    "domain_object",
                    "TODO-ITEM-001",
                    "Summary",
                    "plain",
                    "field-todo-item-001-summary",
                ),
            )
            visible_links = html.split('<lattice-links-panel slot="links">', 1)[
                1
            ].split("</lattice-links-panel>", 1)[0]
            self.assertIn("One list", visible_links)
            self.assertNotIn("Use TodoItem for renderer example", visible_links)
            self.assertIn('<details class="raw-unit">', html)
            self.assertIn("<summary>Raw JSON</summary>", html)
            self.assertIn("<lattice-search", html)
            self.assertIn("lattice-search-index", html)
            self.assertIn('href="../style.css"', html)
            self.assertIn(
                '<lattice-copy-id slot="actions" value="TODO-ITEM-001">', html
            )
            self.assertNotIn("owner:", html.split('<lattice-main slot="main"', 1)[1])
            self.assertIn('<span slot="eyebrow">Domain Object</span>', html)
            self.assertLess(
                html.index("field-table"),
                html.index('<details class="raw-unit">'),
            )

    def test_audit_requires_test_coverage_for_configured_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            config_path = root / "lattice.yml"
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
                any(issue.code == "LATTICE-COVERAGE-001" for issue in issues)
            )

    def test_audit_flags_unknown_lattice_id_in_declared_artifact_roots(self) -> None:
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

            self.assertTrue(any(issue.code == "LATTICE-REF-004" for issue in issues))

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
            path = root / ".lattice/specs/rogue" / f"{rogue_id}.json"
            path.parent.mkdir()
            path.write_text(json.dumps(rogue), encoding="utf-8")

            registry = load_registry(load_config(root))

            self.assertTrue(
                any(issue.code == "LATTICE-KIND-001" for issue in registry.issues)
            )

    def test_domain_object_core_schema_is_semantically_thin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            path = root / ".lattice/specs/glossary/PROJECT-DOMAIN-001.json"
            spec = json.loads(path.read_text(encoding="utf-8"))
            spec["fields"] = [{"name": "id", "type": "string", "required": "yes"}]
            path.write_text(json.dumps(spec), encoding="utf-8")

            registry = load_registry(load_config(root))

            self.assertFalse(
                any(
                    issue.code.startswith("LATTICE-DOMAIN") for issue in registry.issues
                )
            )

    def test_verify_runs_type_configured_project_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            verification = root / ".lattice/specs/verifications/PROJECT-VERIFY-001.json"
            data = json.loads(verification.read_text(encoding="utf-8"))
            data["command"] = "python -c 'raise SystemExit(3)'"
            verification.write_text(json.dumps(data), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            issues = verify(config, registry)

            self.assertTrue(any(issue.code == "LATTICE-VERIFY-001" for issue in issues))


if __name__ == "__main__":
    unittest.main()
