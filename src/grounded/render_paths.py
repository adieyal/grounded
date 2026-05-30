from __future__ import annotations

from pathlib import Path

from .models import GroundedConfig, Spec


def unit_output_path(config: GroundedConfig, spec: Spec) -> Path:
    return config.generated_docs_dir / "units" / f"{slugify(spec.id)}.html"


def href_for(from_path: Path, to_path: Path) -> str:
    return (
        to_path.relative_to(from_path.parent).as_posix()
        if to_path.parent == from_path.parent
        else _relative_path(from_path.parent, to_path)
    )


def _relative_path(from_dir: Path, to_path: Path) -> str:
    import os

    return os.path.relpath(to_path, from_dir).replace("\\", "/")


def slugify(value: object) -> str:
    text = str(value).lower()
    safe = []
    for char in text:
        safe.append(char if char.isalnum() else "-")
    return "-".join(part for part in "".join(safe).split("-") if part)


def field_anchor(unit_id: object, field_name: object) -> str:
    return f"field-{slugify(unit_id)}-{slugify(field_name)}"
