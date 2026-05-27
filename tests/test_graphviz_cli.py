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

            depth_one = graphviz_dot_for(registry, item_id, depth=1)
            self.assertIn(f'"{item_id}" -> "{list_id}";', depth_one)
            self.assertIn(f'"{rule_id}" -> "{item_id}";', depth_one)
            self.assertNotIn(status_id, depth_one)

            only_domain = graphviz_dot_for(
                registry, item_id, depth=2, include_types={"domain_object"}
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


if __name__ == "__main__":
    unittest.main()
