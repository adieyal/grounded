from __future__ import annotations

from pathlib import Path

from .models import LatticeConfig


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "lattice.yml").exists():
            return candidate
    return current


def load_config(root: Path | None = None) -> LatticeConfig:
    project_root = (root or find_project_root()).resolve()
    config_path = project_root / "lattice.yml"
    config = LatticeConfig.default(project_root)
    if not config_path.exists():
        return config

    values: dict[str, str] = {}
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    specs_dir = project_root / values.get("specs_dir", "lattice/specs")
    type_registry_path = project_root / values.get("type_registry_path", "lattice/registry/spec-types.json")
    schemas_dir = project_root / values.get("schemas_dir", "lattice/schemas")
    templates_dir = project_root / values.get("templates_dir", "lattice/renderers/templates")
    styles_dir = project_root / values.get("styles_dir", "lattice/styles")
    docs_dir = project_root / values.get("generated_docs_dir", "lattice/generated/docs")
    llm_dir = project_root / values.get("generated_llm_dir", "lattice/generated/llm")
    search_index_path = project_root / values.get("search_index_path", "lattice/generated/docs/search-index.json")
    test_kinds = values.get("required_test_kinds", "business_rule,example")
    required_test_kinds = frozenset(item.strip() for item in test_kinds.split(",") if item.strip())
    audit_roots_value = values.get("audit_roots", "src,tests,docs,README.md,AGENTS.md")
    audit_roots = tuple(project_root / item.strip() for item in audit_roots_value.split(",") if item.strip())

    return LatticeConfig(
        root=project_root,
        specs_dir=specs_dir,
        type_registry_path=type_registry_path,
        schemas_dir=schemas_dir,
        templates_dir=templates_dir,
        styles_dir=styles_dir,
        generated_docs_dir=docs_dir,
        generated_llm_dir=llm_dir,
        search_index_path=search_index_path,
        required_test_kinds=required_test_kinds,
        audit_roots=audit_roots,
    )
