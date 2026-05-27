from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .rich_text import rich_text_reference_ids


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class LatticeConfig:
    root: Path
    specs_dir: Path
    type_registry_path: Path
    schemas_dir: Path
    templates_dir: Path
    styles_dir: Path
    generated_docs_dir: Path
    generated_llm_dir: Path
    search_index_path: Path
    docs_title: str = "Project Memory"
    docs_eyebrow: str = "Project memory"
    docs_description: str = (
        "Generated from typed Lattice knowledge units. Search, backlinks, and "
        "links are derived from the same registry."
    )
    docs_nav_label: str = "Project Docs"
    docs_background_title: str = "Lattice background"
    docs_background_description: str = (
        "These units explain the documentation system, guardrails, and "
        "generated metadata. They are available for traceability, but they are "
        "not the primary project domain."
    )
    required_test_kinds: frozenset[str] = field(
        default_factory=lambda: frozenset({"business_rule", "example"})
    )
    audit_roots: tuple[Path, ...] = ()

    @classmethod
    def default(
        cls, root: Path, *, lattice_dir: Path | str = ".lattice"
    ) -> "LatticeConfig":
        lattice_path = Path(lattice_dir)
        if not lattice_path.is_absolute():
            lattice_path = root / lattice_path
        return cls(
            root=root,
            specs_dir=lattice_path / "specs",
            type_registry_path=lattice_path / "registry" / "spec-types.json",
            schemas_dir=lattice_path / "schemas",
            templates_dir=lattice_path / "renderers" / "templates",
            styles_dir=lattice_path / "styles",
            generated_docs_dir=lattice_path / "generated" / "docs",
            generated_llm_dir=lattice_path / "generated" / "llm",
            search_index_path=lattice_path / "generated" / "docs" / "search-index.json",
            audit_roots=(
                root / "src",
                root / "tests",
                root / "docs",
                root / "README.md",
                root / "AGENTS.md",
            ),
        )


@dataclass(frozen=True)
class Spec:
    id: str
    kind: str
    path: Path
    data: JsonObject

    @property
    def type(self) -> str:
        return self.kind

    @property
    def owner(self) -> str | None:
        value = self.data.get("owner")
        return value if isinstance(value, str) and value else None

    @property
    def short_name(self) -> str | None:
        value = self.data.get("short_name")
        return value if isinstance(value, str) and value else None

    @property
    def display_name(self) -> str:
        return self.short_name or self.data.get("name", self.id)

    @property
    def tags(self) -> tuple[str, ...]:
        value = self.data.get("tags", [])
        if not isinstance(value, list):
            return ()
        return tuple(tag for tag in value if isinstance(tag, str) and tag)

    @property
    def status(self) -> str:
        value = self.data.get("status")
        return value if isinstance(value, str) else "active"

    @property
    def description(self) -> str:
        value = self.data.get("description") or self.statement
        return value if isinstance(value, str) else ""

    @property
    def references(self) -> tuple[str, ...]:
        refs = (
            [*self.data.get("references", [])]
            if isinstance(self.data.get("references", []), list)
            else []
        )
        links = self.data.get("links", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, str):
                    refs.append(link)
                elif isinstance(link, dict) and isinstance(link.get("target_id"), str):
                    refs.append(link["target_id"])
        if not isinstance(refs, list):
            return ()
        refs.extend(rich_text_reference_ids(self.data))
        return tuple(dict.fromkeys(ref for ref in refs if isinstance(ref, str)))

    @property
    def tests(self) -> tuple[str, ...]:
        tests = self.data.get("tests", [])
        if not isinstance(tests, list):
            return ()
        return tuple(test for test in tests if isinstance(test, str))

    @property
    def statement(self) -> str:
        value = (
            self.data.get("statement")
            or self.data.get("definition")
            or self.data.get("summary")
            or self.data.get("gap")
            or self.data.get("decision")
            or self.data.get("description")
            or self.data.get("name")
            or ""
        )
        return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    path: Path | None = None
    severity: str = "error"

    def format(self, root: Path) -> str:
        location = ""
        if self.path is not None:
            try:
                location = f"{self.path.relative_to(root)}: "
            except ValueError:
                location = f"{self.path}: "
        return f"[{self.severity.upper()}] {self.code}: {location}{self.message}"
