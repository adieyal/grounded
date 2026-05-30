from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lattice.bootstrap import init_project
from lattice.cli import main
from lattice.config import load_config
from lattice.graphviz import graphviz_dot_for
from lattice.registry import load_registry


class GraphvizCliTests(unittest.TestCase):
    def test_graphviz_dot_traverses_incoming_and_outgoing_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            registry_path = root / ".lattice/registry/spec-types.json"
            type_registry = json.loads(registry_path.read_text(encoding="utf-8"))
            type_registry["lifecycle_type"] = {
                "extends": "knowledge_unit",
                "reference_fields": ["references"],
                "schema": {
                    "type": "object",
                    "required": ["id", "name", "owner", "status", "description"],
                    "properties": {
                        "kind": {"const": "lifecycle_type"},
                    },
                    "additionalProperties": True,
                },
            }
            type_registry["lifecycle_value"] = {
                "extends": "knowledge_unit",
                "schema": {
                    "type": "object",
                    "required": ["id", "name", "owner", "status", "description"],
                    "properties": {
                        "kind": {"const": "lifecycle_value"},
                    },
                    "additionalProperties": True,
                },
            }
            registry_path.write_text(json.dumps(type_registry), encoding="utf-8")
            specs_dir = root / ".lattice/specs/examples"
            specs_dir.mkdir(parents=True)
            item_id = "TODO" + "-ITEM-001"
            list_id = "TODO" + "-LIST-001"
            rule_id = "TODO" + "-RULE-001"
            status_id = "TODO" + "-STATUS-001"
            for spec in (
                {
                    "id": item_id,
                    "kind": "domain_object",
                    "name": "TodoItem",
                    "owner": "todo",
                    "status": "active",
                    "description": "A tracked task.",
                    "references": [list_id],
                },
                {
                    "id": list_id,
                    "kind": "domain_object",
                    "name": "TodoList",
                    "owner": "todo",
                    "status": "active",
                    "description": "A collection of tasks.",
                    "references": [status_id],
                },
                {
                    "id": rule_id,
                    "kind": "schema_gap",
                    "name": "Todo ownership",
                    "owner": "todo",
                    "status": "active",
                    "description": "Documents a relationship pointing at the item.",
                    "gap": "Todo ownership needs a durable rule.",
                    "suggested_improvement": "Create a business rule.",
                    "references": [item_id],
                },
                {
                    "id": status_id,
                    "kind": "enum",
                    "name": "TodoStatus",
                    "owner": "todo",
                    "status": "active",
                    "description": "Task status values.",
                    "values": ["open", "done"],
                },
            ):
                (specs_dir / f"{spec['id']}.json").write_text(
                    json.dumps(spec), encoding="utf-8"
                )

            registry = load_registry(load_config(root))

            depth_one = graphviz_dot_for(registry, item_id, depth=1, profile="debug")
            self.assertIn(f'"{item_id}" -> "{list_id}";', depth_one)
            self.assertIn(f'"{rule_id}" -> "{item_id}";', depth_one)
            self.assertNotIn(status_id, depth_one)

            only_domain = graphviz_dot_for(
                registry,
                item_id,
                depth=2,
                include_types={"domain_object"},
                profile="debug",
            )
            self.assertIn(f'"{item_id}" -> "{list_id}";', only_domain)
            self.assertNotIn(rule_id, only_domain)
            self.assertNotIn(status_id, only_domain)

            output = root / "graph.dot"
            result = main(
                [
                    "--root",
                    str(root),
                    "graph",
                    item_id,
                    "--depth",
                    "2",
                    "--profile",
                    "debug",
                    "--exclude-type",
                    "schema_gap",
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(0, result)
            dot = output.read_text(encoding="utf-8")
            self.assertIn("digraph lattice", dot)
            self.assertIn(f'"{list_id}" -> "{status_id}";', dot)
            self.assertNotIn(rule_id, dot)

    def test_docs_profile_uses_structured_labels_and_focus_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            specs_dir = root / ".lattice/specs/examples"
            specs_dir.mkdir(parents=True)
            item_id = "TODO" + "-ITEM-001"
            list_id = "TODO" + "-LIST-001"
            for spec in (
                {
                    "id": item_id,
                    "kind": "domain_object",
                    "name": "TodoItem",
                    "owner": "todo",
                    "status": "active",
                    "description": "A tracked task.",
                    "references": [list_id],
                },
                {
                    "id": list_id,
                    "kind": "domain_object",
                    "name": "TodoList",
                    "owner": "todo",
                    "status": "active",
                    "description": "A collection of tasks.",
                },
            ):
                (specs_dir / f"{spec['id']}.json").write_text(
                    json.dumps(spec), encoding="utf-8"
                )

            registry = load_registry(load_config(root))
            dot = graphviz_dot_for(registry, item_id, depth=1, profile="docs")

            self.assertIn("shape=plain", dot)
            self.assertIn("subgraph cluster_domain_object", dot)
            self.assertIn("<B>TodoItem</B>", dot)
            self.assertIn(f'<FONT FACE="monospace" POINT-SIZE="10">{item_id}</FONT>', dot)
            self.assertIn("domain object", dot)
            self.assertIn('COLOR="#ff6a00"', dot)
            self.assertNotIn(f'label="TodoItem\\\\ndomain_object\\\\n{item_id}"', dot)

    def test_docs_profile_collapses_lifecycle_values_but_debug_keeps_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            specs_dir = root / ".lattice/specs/examples"
            specs_dir.mkdir(parents=True)
            item_id = "TODO" + "-ITEM-001"
            status_type_id = "TODO" + "-STATUS" + "-TYPE-001"
            open_id = "TODO" + "-STATUS-001"
            done_id = "TODO" + "-STATUS-002"
            for spec in (
                {
                    "id": item_id,
                    "kind": "domain_object",
                    "name": "TodoItem",
                    "owner": "todo",
                    "status": "active",
                    "description": "A tracked task.",
                    "references": [status_type_id],
                },
                {
                    "id": status_type_id,
                    "kind": "lifecycle_type",
                    "name": "TodoStatus",
                    "owner": "todo",
                    "status": "active",
                    "description": "Task status values.",
                    "references": [open_id, done_id],
                },
                {
                    "id": open_id,
                    "kind": "lifecycle_value",
                    "name": "Open",
                    "owner": "todo",
                    "status": "active",
                    "description": "Task is open.",
                },
                {
                    "id": done_id,
                    "kind": "lifecycle_value",
                    "name": "Done",
                    "owner": "todo",
                    "status": "active",
                    "description": "Task is done.",
                },
            ):
                (specs_dir / f"{spec['id']}.json").write_text(
                    json.dumps(spec), encoding="utf-8"
                )

            registry = load_registry(load_config(root))
            docs_dot = graphviz_dot_for(registry, item_id, depth=2, profile="docs")
            debug_dot = graphviz_dot_for(registry, item_id, depth=2, profile="debug")

            self.assertIn(open_id, debug_dot)
            self.assertIn(done_id, debug_dot)
            self.assertNotIn(f'"{open_id}" [', docs_dot)
            self.assertNotIn(f'"{done_id}" [', docs_dot)
            self.assertIn("Open | Done", docs_dot)

    def test_cli_accepts_docs_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            output = root / "graph.dot"

            result = main(
                [
                    "--root",
                    str(root),
                    "graph",
                    "PROJECT-GAP-001",
                    "--profile",
                    "docs",
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(0, result)
            self.assertIn("shape=plain", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
