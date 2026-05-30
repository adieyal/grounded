from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from grounded.bootstrap import init_project
from grounded.config import load_config
from grounded.infrastructure.project_memory_json.json_type_source import (
    DEFAULT_TYPE_REGISTRY,
)
from grounded.registry import load_registry
from grounded.render import render_all
from grounded.trust_policy import TRUST_STATUSES
from grounded.trust_policy import TRUST_STATUS_DESCRIPTIONS
from grounded.verify import verify


CLAIM_ID = "-".join(("PROJECT", "CLAIM", "001"))
VERIFY_CLAIM_ID = "-".join(("PROJECT", "VERIFY", "CLAIM", "001"))
OTHER_ID = "-".join(("PROJECT", "OTHER", "001"))
VERIFY_MISSING_ID = "-".join(("PROJECT", "VERIFY", "MISSING", "001"))
VERIFY_BAD_ID = "-".join(("PROJECT", "VERIFY", "BAD", "001"))
VERIFY_RELATIVE_ID = "-".join(("PROJECT", "VERIFY", "RELATIVE", "001"))
BROKEN_ID = "-".join(("PROJECT", "BROKEN", "001"))
MISSING_ID = "-".join(("PROJECT", "MISSING", "001"))
SHAPE_ID = "-".join(("PROJECT", "SHAPE", "001"))


class TrustCredibilityTests(unittest.TestCase):
    def test_invalid_trust_status_fails_validation(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "certain",
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-001")

    def test_trust_status_vocabulary_is_synchronized(self) -> None:
        root = Path(__file__).resolve().parents[1]
        enum_spec = json.loads(
            (root / "grounded/specs/enums/GROUNDED-TRUST-STATUS-001.json").read_text(
                encoding="utf-8"
            )
        )
        schema_values = DEFAULT_TYPE_REGISTRY["registry_unit"]["schema"]["properties"][
            "trust_status"
        ]["enum"]

        self.assertEqual(list(TRUST_STATUSES), schema_values)
        self.assertEqual(list(TRUST_STATUSES), enum_spec["values"])
        self.assertEqual(TRUST_STATUS_DESCRIPTIONS, enum_spec["value_definitions"])

    def test_lifecycle_status_remains_separate_from_trust_status(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "status": "draft",
                    "trust_status": "verified",
                },
            )

            registry = load_registry(load_config(root))

            self.assertNoIssue(registry.issues, "GROUNDED-SCHEMA-006")
            self.assertNoIssue(registry.issues, "GROUNDED-TRUST-001")
            self.assertEqual("draft", registry.by_id[CLAIM_ID].status)
            self.assertEqual(
                "verified",
                registry.by_id[CLAIM_ID].data["trust_status"],
            )

    def test_verified_claim_without_verification_fails_validation(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "verified",
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-002")

    def test_verify_reports_verified_claim_without_verification_refs(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "verified",
                },
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = verify(config, registry)

            self.assertIssue(issues, "GROUNDED-TRUST-002")

    def test_verified_claim_linked_to_inactive_verification_fails_validation(
        self,
    ) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "verified",
                    "verification_refs": [VERIFY_CLAIM_ID],
                },
            )
            write_spec(
                root,
                "verifications",
                verification(
                    VERIFY_CLAIM_ID,
                    target=CLAIM_ID,
                    status="retired",
                ),
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-003")
            self.assertIssue(registry.issues, "GROUNDED-TRUST-002")

    def test_verified_claim_with_wrong_verification_target_fails_validation(
        self,
    ) -> None:
        with initialized_project() as root:
            write_spec(root, "examples", claim(OTHER_ID))
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "verified",
                    "verification_refs": [VERIFY_CLAIM_ID],
                },
            )
            write_spec(
                root,
                "verifications",
                verification(VERIFY_CLAIM_ID, target=OTHER_ID),
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-TRUST-004")

    def test_active_verification_with_missing_command_fails_validation(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "verifications",
                {
                    "id": VERIFY_MISSING_ID,
                    "kind": "verification",
                    "name": "Missing command",
                    "owner": "project",
                    "status": "active",
                    "description": "A verification with no command.",
                    "target": "PROJECT-GAP-001",
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-VERIFY-002")

    def test_active_verification_with_unavailable_executable_fails_validation(
        self,
    ) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "verifications",
                verification(
                    VERIFY_BAD_ID,
                    target="PROJECT-GAP-001",
                    command="definitely-not-grounded-executable --version",
                ),
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-VERIFY-003")

    def test_relative_verification_command_resolves_from_project_root(self) -> None:
        with initialized_project() as root:
            script = root / "scripts/check.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            write_spec(
                root,
                "verifications",
                verification(
                    VERIFY_RELATIVE_ID,
                    target="PROJECT-GAP-001",
                    command="./scripts/check.sh",
                ),
            )
            config = load_config(root)
            registry = load_registry(config)

            self.assertNoIssue(registry.issues, "GROUNDED-VERIFY-003")
            self.assertEqual([], verify(config, registry))

    def test_active_verification_with_failing_command_fails_verify(self) -> None:
        with initialized_project() as root:
            update_spec(
                root / ".grounded/specs/verifications/PROJECT-VERIFY-001.json",
                command="python -c 'raise SystemExit(3)'",
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = verify(config, registry)

            self.assertIssue(issues, "GROUNDED-VERIFY-001")

    def test_verification_timeout_fails_verify(self) -> None:
        with initialized_project() as root:
            update_spec(
                root / ".grounded/specs/verifications/PROJECT-VERIFY-001.json",
                command="python -c 'import time; time.sleep(1)'",
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = verify(config, registry, timeout_seconds=0.01)

            self.assertIssue(issues, "GROUNDED-VERIFY-004")

    def test_verify_deduplicates_identical_commands(self) -> None:
        with initialized_project() as root:
            script = root / "scripts/count.py"
            counter = root / "counter.txt"
            script.parent.mkdir(parents=True)
            script.write_text(
                (
                    "from pathlib import Path\n"
                    "path = Path('counter.txt')\n"
                    "count = int(path.read_text() or '0') if path.exists() else 0\n"
                    "path.write_text(str(count + 1))\n"
                ),
                encoding="utf-8",
            )
            command = "python scripts/count.py"
            write_spec(root, "examples", claim(CLAIM_ID))
            write_spec(root, "examples", claim(OTHER_ID))
            write_spec(
                root,
                "verifications",
                verification(
                    "-".join(("PROJECT", "VERIFY", "DEDUP", "001")),
                    target=CLAIM_ID,
                    command=command,
                ),
            )
            write_spec(
                root,
                "verifications",
                verification(
                    "-".join(("PROJECT", "VERIFY", "DEDUP", "002")),
                    target=OTHER_ID,
                    command=command,
                ),
            )
            config = load_config(root)
            registry = load_registry(config)

            self.assertEqual([], verify(config, registry))

            self.assertEqual("1", counter.read_text(encoding="utf-8"))

    def test_verify_excludes_test_bindings_by_default(self) -> None:
        with initialized_project() as root:
            enable_test_binding_type(root)
            write_spec(root, "examples", claim(CLAIM_ID))
            write_spec(
                root,
                "test_bindings",
                binding_spec(
                    "-".join(("PROJECT", "TEST", "VERIFY", "001")),
                    target=CLAIM_ID,
                    test="python -c 'raise SystemExit(3)'",
                ),
            )
            config = load_config(root)
            registry = load_registry(config)

            self.assertEqual([], verify(config, registry))

    def test_verify_can_include_test_bindings(self) -> None:
        with initialized_project() as root:
            enable_test_binding_type(root)
            write_spec(root, "examples", claim(CLAIM_ID))
            write_spec(
                root,
                "test_bindings",
                binding_spec(
                    "-".join(("PROJECT", "TEST", "VERIFY", "001")),
                    target=CLAIM_ID,
                    test="python -c 'raise SystemExit(3)'",
                ),
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = verify(config, registry, include_test_bindings=True)

            self.assertIssue(issues, "GROUNDED-VERIFY-001")

    def test_verified_claim_with_failing_verification_fails_verify(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "verified",
                    "verification_refs": [VERIFY_CLAIM_ID],
                },
            )
            write_spec(
                root,
                "verifications",
                verification(
                    VERIFY_CLAIM_ID,
                    target=CLAIM_ID,
                    command="python -c 'raise SystemExit(3)'",
                ),
            )
            config = load_config(root)
            registry = load_registry(config)

            issues = verify(config, registry)

            self.assertIssue(issues, "GROUNDED-VERIFY-001")
            self.assertIssue(issues, "GROUNDED-VERIFY-006")

    def test_verified_claim_with_passing_verification_passes(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    **claim(CLAIM_ID),
                    "trust_status": "verified",
                    "verification_refs": [VERIFY_CLAIM_ID],
                },
            )
            write_spec(
                root,
                "verifications",
                verification(VERIFY_CLAIM_ID, target=CLAIM_ID),
            )
            config = load_config(root)
            registry = load_registry(config)

            self.assertEqual([], registry.issues)
            self.assertEqual([], verify(config, registry))

    def test_existing_duplicate_id_check_remains(self) -> None:
        with initialized_project() as root:
            duplicate = claim(CLAIM_ID)
            write_spec(root, "examples", duplicate)
            other_path = root / ".grounded/specs/other" / f"{CLAIM_ID}.json"
            other_path.parent.mkdir(parents=True, exist_ok=True)
            other_path.write_text(json.dumps(duplicate), encoding="utf-8")

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-ID-001")

    def test_existing_reference_check_remains(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    "id": BROKEN_ID,
                    "kind": "domain_object",
                    "name": "Broken",
                    "owner": "project",
                    "status": "active",
                    "description": "Broken reference.",
                    "references": [MISSING_ID],
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-REF-001")

    def test_existing_schema_check_remains(self) -> None:
        with initialized_project() as root:
            write_spec(
                root,
                "examples",
                {
                    "id": SHAPE_ID,
                    "kind": "domain_object",
                    "name": "Invalid shape",
                    "owner": "project",
                    "status": "active",
                    "description": "",
                },
            )

            registry = load_registry(load_config(root))

            self.assertIssue(registry.issues, "GROUNDED-SCHEMA-006")

    def test_existing_render_stale_check_remains(self) -> None:
        with initialized_project() as root:
            config = load_config(root)
            registry = load_registry(config)
            render_all(config, registry)
            obsolete = root / ".grounded/generated/docs/units/obsolete.html"
            obsolete.write_text("stale", encoding="utf-8")

            self.assertIn(
                ".grounded/generated/docs/units/obsolete.html",
                render_all(config, registry, check=True),
            )

    def assertIssue(self, issues: list[object], code: str) -> None:
        self.assertTrue(any(getattr(issue, "code", None) == code for issue in issues))

    def assertNoIssue(self, issues: list[object], code: str) -> None:
        self.assertFalse(any(getattr(issue, "code", None) == code for issue in issues))


@contextmanager
def initialized_project() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        init_project(root)
        update_spec(
            root / ".grounded/specs/verifications/PROJECT-VERIFY-001.json",
            command="python -c 'raise SystemExit(0)'",
        )
        yield root


def claim(spec_id: str) -> dict[str, object]:
    return {
        "id": spec_id,
        "kind": "domain_object",
        "name": "Claim",
        "owner": "project",
        "status": "active",
        "description": "A claim-bearing domain object.",
    }


def verification(
    spec_id: str,
    *,
    target: str,
    command: str = "python -c 'raise SystemExit(0)'",
    status: str = "active",
) -> dict[str, object]:
    return {
        "id": spec_id,
        "kind": "verification",
        "name": "Claim verification",
        "owner": "project",
        "status": status,
        "description": "A verification command for a claim.",
        "target": target,
        "command": command,
    }


def binding_spec(spec_id: str, *, target: str, test: str) -> dict[str, object]:
    return {
        "id": spec_id,
        "kind": "test_binding",
        "name": "Claim test binding",
        "owner": "project",
        "status": "active",
        "description": "A test binding for a claim.",
        "target": target,
        "test": test,
    }


def enable_test_binding_type(root: Path) -> None:
    type_registry_path = root / ".grounded/registry/spec-types.json"
    type_registry = json.loads(type_registry_path.read_text(encoding="utf-8"))
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
        "verification_fields": ["test"],
    }
    type_registry_path.write_text(json.dumps(type_registry), encoding="utf-8")


def write_spec(root: Path, folder: str, data: dict[str, object]) -> Path:
    path = root / ".grounded/specs" / folder / f"{data['id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def update_spec(path: Path, **updates: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(updates)
    path.write_text(json.dumps(data), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
