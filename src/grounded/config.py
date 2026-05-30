from __future__ import annotations

from pathlib import Path

from .models import GroundedConfig


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "grounded.yml").exists():
            return candidate
    return current


def load_config(root: Path | None = None) -> GroundedConfig:
    project_root = (root or find_project_root()).resolve()
    config_path = project_root / "grounded.yml"
    config = GroundedConfig.default(project_root)
    if not config_path.exists():
        return config

    values: dict[str, str] = {}
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    specs_dir = project_root / values.get(
        "specs_dir", str(config.specs_dir.relative_to(project_root))
    )
    type_registry_path = project_root / values.get(
        "type_registry_path", str(config.type_registry_path.relative_to(project_root))
    )
    schemas_dir = project_root / values.get(
        "schemas_dir", str(config.schemas_dir.relative_to(project_root))
    )
    templates_dir = project_root / values.get(
        "templates_dir", str(config.templates_dir.relative_to(project_root))
    )
    styles_dir = project_root / values.get(
        "styles_dir", str(config.styles_dir.relative_to(project_root))
    )
    docs_dir = project_root / values.get(
        "generated_docs_dir", str(config.generated_docs_dir.relative_to(project_root))
    )
    llm_dir = project_root / values.get(
        "generated_llm_dir", str(config.generated_llm_dir.relative_to(project_root))
    )
    search_index_path = project_root / values.get(
        "search_index_path", str(config.search_index_path.relative_to(project_root))
    )
    docs_title = values.get("docs_title", config.docs_title)
    docs_eyebrow = values.get("docs_eyebrow", config.docs_eyebrow)
    docs_description = values.get("docs_description", config.docs_description)
    docs_nav_label = values.get("docs_nav_label", config.docs_nav_label)
    docs_background_title = values.get(
        "docs_background_title", config.docs_background_title
    )
    docs_background_description = values.get(
        "docs_background_description", config.docs_background_description
    )
    test_kinds = values.get("required_test_kinds", "business_rule,example")
    required_test_kinds = frozenset(
        item.strip() for item in test_kinds.split(",") if item.strip()
    )
    audit_roots_value = values.get("audit_roots", "src,tests,docs,README.md,AGENTS.md")
    audit_roots = tuple(
        project_root / item.strip()
        for item in audit_roots_value.split(",")
        if item.strip()
    )

    return GroundedConfig(
        root=project_root,
        specs_dir=specs_dir,
        type_registry_path=type_registry_path,
        schemas_dir=schemas_dir,
        templates_dir=templates_dir,
        styles_dir=styles_dir,
        generated_docs_dir=docs_dir,
        generated_llm_dir=llm_dir,
        search_index_path=search_index_path,
        docs_title=docs_title,
        docs_eyebrow=docs_eyebrow,
        docs_description=docs_description,
        docs_nav_label=docs_nav_label,
        docs_background_title=docs_background_title,
        docs_background_description=docs_background_description,
        required_test_kinds=required_test_kinds,
        audit_roots=audit_roots,
    )
