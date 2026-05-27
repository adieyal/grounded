from __future__ import annotations

from pathlib import Path

from .models import LatticeConfig, Spec
from .registry import SpecRegistry
from .render_constants import INDEX_FILENAME
from .render_paths import slugify


SLICE_INDEX_TEMPLATE = "slice-index.html.j2"


def slice_specs(registry: SpecRegistry) -> list[Spec]:
    return sorted(
        (spec for spec in registry.active_specs if spec.kind == "slice"),
        key=lambda spec: spec.id,
    )


def slice_members(slice_spec: Spec, registry: SpecRegistry) -> list[Spec]:
    members = slice_spec.data.get("members", [])
    if not isinstance(members, list):
        return []
    active_by_id = {spec.id: spec for spec in registry.active_specs}
    return [
        active_by_id[member_id]
        for member_id in members
        if isinstance(member_id, str) and member_id in active_by_id
    ]


def slice_slug(slice_spec: Spec) -> str:
    value = slice_spec.data.get("slug")
    if isinstance(value, str) and value.strip():
        return slugify(value) or slugify(slice_spec.id)
    return slugify(slice_spec.display_name) or slugify(slice_spec.id)


def slice_output_path(config: LatticeConfig, slice_spec: Spec) -> Path:
    return (
        config.generated_docs_dir / "slices" / slice_slug(slice_spec) / INDEX_FILENAME
    )


def slice_template_name(slice_spec: Spec) -> str:
    value = slice_spec.data.get("index_template")
    return value if isinstance(value, str) and value.strip() else SLICE_INDEX_TEMPLATE


def slice_description(slice_spec: Spec) -> str:
    value = slice_spec.data.get("description") or slice_spec.statement
    return value if isinstance(value, str) else ""


def slice_style_source(config: LatticeConfig, slice_spec: Spec) -> Path | None:
    value = slice_spec.data.get("style_path")
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return path if path.is_absolute() else config.root / path


def slice_style_output_path(config: LatticeConfig, slice_spec: Spec) -> Path | None:
    source = slice_style_source(config, slice_spec)
    if source is None:
        return None
    return slice_output_path(config, slice_spec).parent / source.name
