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
from lattice.registry import load_registry
from lattice.render import render_all
from lattice.verify import verify


class LatticeTests(unittest.TestCase):
    def test_init_creates_specs_skill_and_agents_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = init_project(root)

            self.assertIn(root / "lattice.yml", created)
            self.assertTrue((root / "lattice/specs/rules/PROJECT-RULE-001.json").exists())
            self.assertTrue((root / "lattice/specs/glossary/PROJECT-DOMAIN-001.json").exists())
            self.assertTrue((root / "lattice/specs/schema_gaps/PROJECT-GAP-001.json").exists())
            self.assertTrue((root / "lattice/registry/spec-types.json").exists())
            self.assertTrue((root / "lattice/schemas/spec.schema.json").exists())
            self.assertTrue((root / "lattice/templates/domain_object.json").exists())
            self.assertTrue((root / "lattice/templates/schema_gap.json").exists())
            self.assertFalse((root / "lattice/renderers/templates/unit.html.j2").exists())
            self.assertTrue((root / "skills/lattice-project-memory/SKILL.md").exists())
            self.assertIn(AGENTS_MARKER_START, (root / "AGENTS.md").read_text(encoding="utf-8"))

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
            html = (root / "lattice/generated/docs/project-memory.html").read_text(encoding="utf-8")
            css = (root / "lattice/generated/docs/style.css").read_text(encoding="utf-8")
            search = (root / "lattice/generated/docs/search-index.json").read_text(encoding="utf-8")
            self.assertIn("<main", html)
            self.assertIn("<article", html)
            self.assertIn("data-search-input", html)
            self.assertIn("lattice-registry", html)
            self.assertIn("lattice-link.js", html)
            self.assertIn("Canonical project fact", html)
            self.assertIn("Schema Gap", html)
            self.assertIn('href="style.css"', html)
            self.assertIn(":root", css)
            self.assertIn("Canonical project fact", search)

    def test_audit_requires_test_coverage_for_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            binding = root / "lattice/specs/test_bindings/PROJECT-TEST-001.json"
            binding.unlink()
            rule_path = root / "lattice/specs/rules/PROJECT-RULE-001.json"
            rule = json.loads(rule_path.read_text(encoding="utf-8"))
            rule["tests"] = []
            rule_path.write_text(json.dumps(rule), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)
            issues = audit(config, registry)

            self.assertTrue(any(issue.code == "LATTICE-COVERAGE-001" for issue in issues))

    def test_audit_flags_unknown_lattice_id_in_declared_artifact_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            (root / "docs").mkdir()
            missing_id = "MISSING" + "-RULE-999"
            (root / "docs/spec.md").write_text(f"This references {missing_id}.", encoding="utf-8")

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
            path = root / "lattice/specs/rogue" / f"{rogue_id}.json"
            path.parent.mkdir()
            path.write_text(json.dumps(rogue), encoding="utf-8")

            registry = load_registry(load_config(root))

            self.assertTrue(any(issue.code == "LATTICE-KIND-001" for issue in registry.issues))

    def test_domain_object_core_schema_is_semantically_thin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            path = root / "lattice/specs/glossary/PROJECT-DOMAIN-001.json"
            spec = json.loads(path.read_text(encoding="utf-8"))
            spec["fields"] = [{"name": "id", "type": "string", "required": "yes"}]
            path.write_text(json.dumps(spec), encoding="utf-8")

            registry = load_registry(load_config(root))

            self.assertFalse(any(issue.code.startswith("LATTICE-DOMAIN") for issue in registry.issues))

    def test_verify_runs_type_configured_project_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            binding = root / "lattice/specs/test_bindings/PROJECT-TEST-001.json"
            data = json.loads(binding.read_text(encoding="utf-8"))
            data["test"] = "python -c 'raise SystemExit(3)'"
            binding.write_text(json.dumps(data), encoding="utf-8")

            config = load_config(root)
            registry = load_registry(config)
            issues = verify(config, registry)

            self.assertTrue(any(issue.code == "LATTICE-VERIFY-001" for issue in issues))


if __name__ == "__main__":
    unittest.main()
