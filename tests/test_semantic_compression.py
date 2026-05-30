from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from grounded.audit import audit
from grounded.bootstrap import init_project
from grounded.config import load_config
from grounded.infrastructure.project_memory_json.json_type_source import (
    DEFAULT_TYPE_REGISTRY,
)
from grounded.registry import load_registry
from grounded.render import render_all


CLAIM_ID = "-".join(("PROJECT", "CLAIM", "001"))
DOC_ID = "-".join(("PROJECT", "DOC", "001"))
SECTION_ID = "-".join(("PROJECT", "SECTION", "001"))


class SemanticCompressionTests(unittest.TestCase):
    def test_overlapping_project_registry_categories_match_bundled_defaults(
        self,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        project_registry = json.loads(
            (root / "grounded/registry/spec-types.json").read_text(encoding="utf-8")
        )

        for type_name, type_def in project_registry.items():
            if type_name not in DEFAULT_TYPE_REGISTRY:
                continue
            self.assertEqual(
                DEFAULT_TYPE_REGISTRY[type_name].get("semantic_category"),
                type_def.get("semantic_category"),
                type_name,
            )

    def test_bundled_semantic_category_assignments_are_explicit(self) -> None:
        expected_categories = {
            "domain_object": "authored_knowledge",
            "enum": "authored_knowledge",
            "verification": "registry_infrastructure",
            "schema_gap": "registry_infrastructure",
            "generated_document": "generated_artifact",
            "document_section": "generated_artifact",
            "documentation_set": "generated_artifact",
            "asset": "generated_artifact",
        }

        for type_name, expected_category in expected_categories.items():
            self.assertEqual(
                expected_category,
                DEFAULT_TYPE_REGISTRY[type_name].get("semantic_category"),
                type_name,
            )

    def test_project_extension_semantic_category_assignments_are_explicit(
        self,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        project_registry = json.loads(
            (root / "grounded/registry/spec-types.json").read_text(encoding="utf-8")
        )
        expected_categories = {
            "business_rule": "authored_knowledge",
            "concept": "authored_knowledge",
            "decision": "authored_knowledge",
            "example": "authored_knowledge",
            "workflow": "authored_knowledge",
            "guardrail": "registry_infrastructure",
            "test_binding": "registry_infrastructure",
        }

        for type_name, expected_category in expected_categories.items():
            self.assertEqual(
                expected_category,
                project_registry[type_name].get("semantic_category"),
                type_name,
            )

    def test_semantic_categories_accept_only_approved_values(self) -> None:
        with initialized_project() as root:
            registry_path = root / ".grounded/registry/spec-types.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["domain_object"]["semantic_category"] = "junk_drawer"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            loaded = load_registry(load_config(root))

            self.assertIssue(loaded.issues, "GROUNDED-TYPE-012")

    def test_generated_document_cannot_own_truth(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "docs",
                generated_document(
                    DOC_ID,
                    trust_status="observed",
                    observed_basis="The file exists after rendering.",
                ),
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-005")

    def test_document_section_cannot_own_truth(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "docs",
                {
                    **document_section(source_refs=[]),
                    "trust_status": "checkable",
                    "trust_basis": "A generated section is planned.",
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-005")

    def test_generated_artifact_can_source_authored_specs(self) -> None:
        with initialized_project() as root:
            write_spec(root, "examples", claim(CLAIM_ID))
            write_spec(root, "docs", document_section(source_refs=[CLAIM_ID]))

            registry = load_registry(load_config(root))

            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-005")
            self.assertNoIssue(registry.issues, "GROUNDED-REF-001")

    def test_checkable_claim_requires_verification_or_trust_basis(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "checkable",
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-006")

        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "checkable",
                    "trust_basis": "The check is planned but not wired in this slice.",
                },
            )

            registry = load_registry(load_config(root))

            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-006")

    def test_observed_claim_requires_observation_basis(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "observed",
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-007")

    def test_observed_claim_with_only_generated_source_refs_fails(self) -> None:
        with initialized_project() as root:
            write_spec(root, "docs", generated_document(DOC_ID))
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "observed",
                    "source_refs": [DOC_ID],
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-007")

    def test_observed_claim_with_registry_infrastructure_source_ref_fails(
        self,
    ) -> None:
        with initialized_project() as root:
            source_id = "-".join(("PROJECT", "VERIFY", "001"))
            write_spec(
                root,
                "verifications",
                {
                    "id": source_id,
                    "kind": "verification",
                    "name": "Infrastructure source",
                    "owner": "project",
                    "status": "active",
                    "description": "A proof mechanism, not observational evidence.",
                    "target": CLAIM_ID,
                    "command": "python -c 'raise SystemExit(0)'",
                },
            )
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "observed",
                    "source_refs": [source_id],
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-007")

    def test_observed_claim_with_references_tests_or_examples_only_fails(
        self,
    ) -> None:
        for field in ("references", "tests", "examples"):
            with self.subTest(field=field), initialized_project() as root:
                source_id = "-".join(("PROJECT", "SOURCE", "001"))
                write_spec(root, "examples", claim(source_id))
                write_spec(
                    root,
                    "examples",
                    {
                        **claim(CLAIM_ID),
                        "trust_status": "observed",
                        field: [source_id],
                    },
                )

                registry = load_registry(load_config(root))

                self.assertIssue(registry.issues, "GROUNDED-TRUST-007")

    def test_observed_claim_accepts_non_generated_source_refs(self) -> None:
        with initialized_project() as root:
            source_id = "-".join(("PROJECT", "SOURCE", "001"))
            write_spec(root, "examples", claim(source_id))
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "observed",
                    "source_refs": [source_id],
                },
            )

            registry = load_registry(load_config(root))

            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-007")

    def test_observed_claim_accepts_observed_basis_or_evidence(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "observed",
                    "observed_basis": "Observed in the repository configuration.",
                },
            )

            registry = load_registry(load_config(root))

            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-007")

        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "observed",
                    "evidence": "Observed in a local fixture.",
                },
            )

            registry = load_registry(load_config(root))

            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-007")

    def test_unknown_trust_status_is_allowed_without_stronger_claim(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "unknown",
                },
            )

            registry = load_registry(load_config(root))

            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-001")
            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-002")
            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-006")
            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-007")

    def test_aspirational_trust_status_renders_as_future_intent(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "aspirational",
                },
            )
            config = load_config(root)
            registry = load_registry(config)

            render_all(config, registry)

            page = (
                config.generated_docs_dir / "units" / "project-claim-001.html"
            ).read_text(encoding="utf-8")
            self.assertIn("Aspirational", page)
            self.assertIn("future intent, not current truth", page)

    def test_concept_usage_is_audited_for_catch_all_drift(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "concepts",
                {
                    "id": "PROJECT-CONCEPT-001",
                    "kind": "concept",
                    "name": "Thing",
                    "owner": "project",
                    "status": "active",
                    "description": "A vague concept.",
                },
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = audit(config, registry)

            self.assertIssue(issues, "GROUNDED-CONCEPT-001")

    def test_decision_usage_is_audited_for_shape_drift(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "decisions",
                {
                    "id": "PROJECT-DECISION-001",
                    "kind": "decision",
                    "name": "Do one thing",
                    "owner": "project",
                    "status": "active",
                    "description": "Documents a narrow decision.",
                    "decision": "Keep decisions narrow.",
                    "workflow_steps": ["This belongs in a workflow spec."],
                },
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = audit(config, registry)

            self.assertIssue(issues, "GROUNDED-DECISION-SHAPE-001")

    def test_document_section_cannot_be_canonical_truth_owner(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "docs",
                document_section(
                    source_refs=[],
                    intro="This section must be treated as the source of truth.",
                ),
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = audit(config, registry)

            self.assertIssue(issues, "GROUNDED-DOC-GRAPH-005")

    def test_mixed_document_section_requires_source_refs(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "docs",
                {
                    **document_section(source_refs=[]),
                    "content_mode": "mixed",
                    "intro": "This section mixes local glue with projected source material.",
                },
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = audit(config, registry)

            self.assertIssue(issues, "GROUNDED-DOC-GRAPH-002")

    def test_local_prose_without_claim_language_can_omit_source_refs(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "docs",
                document_section(
                    source_refs=[],
                    intro="This short transition introduces the next generated section.",
                ),
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = audit(config, registry)

            self.assertNoIssue(issues, "GROUNDED-DOC-GRAPH-002")
            self.assertNoIssue(issues, "GROUNDED-DOC-GRAPH-005")

    def assertIssue(self, issues: list[object], code: str) -> None:
        self.assertTrue(any(getattr(issue, "code", None) == code for issue in issues))

    def assertNoIssue(self, issues: list[object], code: str) -> None:
        self.assertFalse(any(getattr(issue, "code", None) == code for issue in issues))


@contextmanager
def initialized_project() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        init_project(root)
        yield root


def claim(spec_id: str) -> dict[str, object]:
    return {
        "id": spec_id,
        "kind": "domain_object",
        "name": "Claim",
        "owner": "project",
        "status": "active",
        "description": "A durable authored claim.",
    }


def generated_document(
    spec_id: str,
    *,
    trust_status: str | None = None,
    observed_basis: str | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "id": spec_id,
        "kind": "generated_document",
        "name": "Generated README",
        "owner": "project",
        "status": "active",
        "description": "Defines a generated document artifact.",
        "output_path": "README.md",
        "format": "markdown",
        "renderer": "markdown_document",
        "write_mode": "protected_block",
        "purpose": "Render a project README.",
        "source_refs": [],
        "section_refs": [],
    }
    if trust_status is not None:
        data["trust_status"] = trust_status
    if observed_basis is not None:
        data["observed_basis"] = observed_basis
    return data


def document_section(
    *,
    source_refs: list[str],
    intro: str = "A generated documentation section.",
) -> dict[str, object]:
    return {
        "id": SECTION_ID,
        "kind": "document_section",
        "name": "Generated section",
        "owner": "project",
        "status": "active",
        "description": "Defines a generated document section.",
        "heading": "Section",
        "heading_level": 2,
        "order": 10,
        "renderer": "source_summary",
        "content_mode": "local_prose" if not source_refs else "sourced",
        "source_refs": source_refs,
        "intro": intro,
    }


def write_spec(root: Path, folder: str, data: dict[str, object]) -> Path:
    path = root / ".grounded/specs" / folder / f"{data['id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
