from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from .edge_policy import (
    EDGE_TYPES,
    SEMANTIC_LAYER_ORDER,
    is_allowed_edge_type,
    is_allowed_semantic_layer,
)
from .modules.project_memory.domain.issues import ProjectMemoryIssue
from .modules.project_memory.domain.model import (
    NormalizedEdge,
    ProjectMemoryTypes,
    ProjectMemoryUnit,
)
from .rich_text import rich_text_reference_ids
from .trust_policy import GENERATED_ARTIFACT_CATEGORY


class EdgeBearingUnit(Protocol):
    id: str
    kind: str
    data: dict[str, object]


LEGACY_LIST_FIELD_EDGE_TYPES = {
    "references": "mentions",
    "examples": "mentions",
    "tests": "tests",
    "verification_refs": "verified_by",
    "section_refs": "contains",
    "document_refs": "contains",
    "members": "contains",
}


def normalized_edges_for_unit(
    unit: EdgeBearingUnit, types: ProjectMemoryTypes | None = None
) -> tuple[NormalizedEdge, ...]:
    edges: list[NormalizedEdge] = []
    edges.extend(_authored_edges_for(unit))
    edges.extend(_legacy_edges_for(unit, types))
    return tuple(_dedupe_edges(edges))


def normalized_edges_for_units(
    units: tuple[EdgeBearingUnit, ...] | list[EdgeBearingUnit],
    types: ProjectMemoryTypes | None = None,
) -> tuple[NormalizedEdge, ...]:
    edges: list[NormalizedEdge] = []
    for unit in units:
        edges.extend(normalized_edges_for_unit(unit, types))
    return tuple(_dedupe_edges(edges))


def validate_edges(
    units: tuple[ProjectMemoryUnit, ...],
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    issues: list[ProjectMemoryIssue] = []
    by_id = {unit.id: unit for unit in units}
    for unit in units:
        issues.extend(_validate_authored_edge_shape(unit))
        semantic_layer = unit.data.get("semantic_layer")
        if semantic_layer is not None and not is_allowed_semantic_layer(semantic_layer):
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-EDGE-009",
                    (
                        f"{unit.id}.semantic_layer must be one of "
                        f"{', '.join(SEMANTIC_LAYER_ORDER)}"
                    ),
                    unit.source_location,
                )
            )
        for edge in normalized_edges_for_unit(unit, types):
            source = by_id.get(edge.source_id, unit)
            issues.extend(_validate_normalized_edge(edge, source, by_id, types))
    return issues


def grouped_edges_by_type(
    edges: tuple[NormalizedEdge, ...] | list[NormalizedEdge],
) -> dict[str, tuple[NormalizedEdge, ...]]:
    grouped: defaultdict[str, list[NormalizedEdge]] = defaultdict(list)
    for edge in edges:
        grouped[edge.edge_type].append(edge)
    return {
        edge_type: tuple(
            sorted(
                grouped[edge_type],
                key=lambda edge: (
                    edge.source_id,
                    edge.target_id,
                    edge.source_field or "",
                    edge.authored,
                ),
            )
        )
        for edge_type in EDGE_TYPES
        if grouped.get(edge_type)
    }


def _authored_edges_for(unit: EdgeBearingUnit) -> list[NormalizedEdge]:
    raw_edges = unit.data.get("edges")
    if not isinstance(raw_edges, list):
        return []
    edges: list[NormalizedEdge] = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, dict):
            continue
        edge_type = raw_edge.get("type")
        target = raw_edge.get("target")
        if isinstance(edge_type, str) and isinstance(target, str) and target.strip():
            edges.append(
                NormalizedEdge(
                    source_id=unit.id,
                    target_id=target,
                    edge_type=edge_type,
                    source_field="edges",
                    authored=True,
                )
            )
    return edges


def _legacy_edges_for(
    unit: EdgeBearingUnit, types: ProjectMemoryTypes | None
) -> list[NormalizedEdge]:
    edges: list[NormalizedEdge] = []
    for field in (*LEGACY_LIST_FIELD_EDGE_TYPES, "source_refs", "asset_refs"):
        edge_type = _legacy_edge_type_for_field(unit, field, types)
        if edge_type is None:
            continue
        raw_refs = unit.data.get(field, [])
        if not isinstance(raw_refs, list):
            continue
        for ref in raw_refs:
            if isinstance(ref, str) and ref:
                edges.append(
                    NormalizedEdge(
                        source_id=unit.id,
                        target_id=ref,
                        edge_type=edge_type,
                        source_field=field,
                        authored=False,
                    )
                )

    if unit.kind == "verification":
        target = unit.data.get("target")
        if isinstance(target, str) and target:
            edges.append(
                NormalizedEdge(
                    source_id=target,
                    target_id=unit.id,
                    edge_type="verified_by",
                    source_field="target",
                    authored=False,
                )
            )
    for ref in rich_text_reference_ids(unit.data):
        edges.append(
            NormalizedEdge(
                source_id=unit.id,
                target_id=ref,
                edge_type="mentions",
                source_field="rich_text",
                authored=False,
            )
        )
    return edges


def _legacy_edge_type_for_field(
    unit: EdgeBearingUnit, field: str, types: ProjectMemoryTypes | None
) -> str | None:
    type_def = types.get(unit.kind) if types is not None else None
    if type_def is not None and any(
        mapping.get("field") == field for mapping in type_def.binding_field_mappings
    ):
        return None
    if field == "source_refs":
        return (
            "derives_from" if _is_generated_artifact_like(unit, types) else "mentions"
        )
    if field == "asset_refs":
        return (
            "contains" if _is_generated_artifact_like(unit, types) else "illustrated_by"
        )
    return LEGACY_LIST_FIELD_EDGE_TYPES.get(field)


def _validate_authored_edge_shape(unit: ProjectMemoryUnit) -> list[ProjectMemoryIssue]:
    raw_edges = unit.data.get("edges")
    if raw_edges is None:
        return []
    if not isinstance(raw_edges, list):
        return [
            ProjectMemoryIssue(
                "GROUNDED-EDGE-001",
                f"{unit.id}.edges must be a list",
                unit.source_location,
            )
        ]

    issues: list[ProjectMemoryIssue] = []
    for index, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, dict):
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-EDGE-002",
                    f"{unit.id}.edges[{index}] must be an object",
                    unit.source_location,
                )
            )
            continue
        edge_type = raw_edge.get("type")
        target = raw_edge.get("target")
        if not is_allowed_edge_type(edge_type):
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-EDGE-003",
                    (
                        f"{unit.id}.edges[{index}].type must be one of "
                        f"{', '.join(EDGE_TYPES)}"
                    ),
                    unit.source_location,
                )
            )
        if not isinstance(target, str) or not target.strip():
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-EDGE-002",
                    f"{unit.id}.edges[{index}].target must be a non-empty string",
                    unit.source_location,
                )
            )
    return issues


def _validate_normalized_edge(
    edge: NormalizedEdge,
    source_unit: ProjectMemoryUnit,
    by_id: dict[str, ProjectMemoryUnit],
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    target = by_id.get(edge.target_id)
    if target is None:
        return [
            ProjectMemoryIssue(
                "GROUNDED-EDGE-004",
                (
                    f"{edge.source_id}.{edge.source_field or 'edge'} "
                    f"{edge.edge_type} points to unknown spec {edge.target_id}"
                ),
                source_unit.source_location,
            )
        ]

    issues: list[ProjectMemoryIssue] = []
    if edge.edge_type == "verified_by":
        issues.extend(_validate_verified_by(edge, source_unit, target))
    elif edge.edge_type in {"documents", "derives_from"}:
        issues.extend(_validate_projection_edge(edge, source_unit, target, types))
    elif edge.edge_type == "illustrated_by" and target.kind != "asset":
        issues.append(
            ProjectMemoryIssue(
                "GROUNDED-EDGE-007",
                f"{edge.source_id} illustrated_by target {target.id} must be an asset",
                source_unit.source_location,
            )
        )
    elif edge.edge_type == "implements" and _is_generated_artifact(target, types):
        issues.append(
            ProjectMemoryIssue(
                "GROUNDED-EDGE-008",
                f"{edge.source_id} implements target {target.id} cannot be generated",
                source_unit.source_location,
            )
        )
    elif edge.edge_type == "depends_on":
        if _is_generated_artifact(target, types):
            issues.append(
                ProjectMemoryIssue(
                    "GROUNDED-EDGE-008",
                    f"{edge.source_id} depends_on target {target.id} cannot be generated",
                    source_unit.source_location,
                )
            )
        issues.extend(_validate_layer_direction(edge, source_unit, target))
    return issues


def _validate_verified_by(
    edge: NormalizedEdge,
    source_unit: ProjectMemoryUnit,
    target: ProjectMemoryUnit,
) -> list[ProjectMemoryIssue]:
    if target.kind not in {"verification", "test_binding"}:
        return [
            ProjectMemoryIssue(
                "GROUNDED-EDGE-005",
                (
                    f"{edge.source_id} verified_by target {target.id} must be "
                    "an active verification or test_binding"
                ),
                source_unit.source_location,
            )
        ]
    if target.status != "active":
        return [
            ProjectMemoryIssue(
                "GROUNDED-EDGE-005",
                f"{edge.source_id} verified_by target {target.id} must be active",
                source_unit.source_location,
            )
        ]
    target_field = target.data.get("target")
    if isinstance(target_field, str) and target_field != edge.source_id:
        return [
            ProjectMemoryIssue(
                "GROUNDED-EDGE-005",
                (
                    f"{edge.source_id} verified_by target {target.id} points at "
                    f"{target_field!r}, not {edge.source_id!r}"
                ),
                source_unit.source_location,
            )
        ]
    return []


def _validate_projection_edge(
    edge: NormalizedEdge,
    source_unit: ProjectMemoryUnit,
    target: ProjectMemoryUnit,
    types: ProjectMemoryTypes,
) -> list[ProjectMemoryIssue]:
    if not _is_generated_artifact(source_unit, types):
        return [
            ProjectMemoryIssue(
                "GROUNDED-EDGE-006",
                (
                    f"{edge.source_id} {edge.edge_type} edge must start from a "
                    "generated artifact"
                ),
                source_unit.source_location,
            )
        ]
    if _is_generated_artifact(target, types):
        return [
            ProjectMemoryIssue(
                "GROUNDED-EDGE-006",
                (
                    f"{edge.source_id} {edge.edge_type} target {target.id} must be "
                    "a non-generated source spec"
                ),
                source_unit.source_location,
            )
        ]
    return []


def _validate_layer_direction(
    edge: NormalizedEdge, source_unit: ProjectMemoryUnit, target: ProjectMemoryUnit
) -> list[ProjectMemoryIssue]:
    source_layer = source_unit.data.get("semantic_layer")
    target_layer = target.data.get("semantic_layer")
    if not isinstance(source_layer, str) or not isinstance(target_layer, str):
        return []
    if (
        source_layer not in SEMANTIC_LAYER_ORDER
        or target_layer not in SEMANTIC_LAYER_ORDER
    ):
        return []
    if SEMANTIC_LAYER_ORDER[source_layer] >= SEMANTIC_LAYER_ORDER[target_layer]:
        return []
    return [
        ProjectMemoryIssue(
            "GROUNDED-EDGE-010",
            (
                f"{edge.source_id} semantic_layer {source_layer} must not depend_on "
                f"{target.id} semantic_layer {target_layer}"
            ),
            source_unit.source_location,
        )
    ]


def _is_generated_artifact(unit: ProjectMemoryUnit, types: ProjectMemoryTypes) -> bool:
    return _is_generated_artifact_like(unit, types)


def _is_generated_artifact_like(
    unit: EdgeBearingUnit, types: ProjectMemoryTypes | None
) -> bool:
    if types is None:
        return unit.kind in {
            "asset",
            "document_section",
            "documentation_set",
            "generated_document",
        }
    type_def = types.get(unit.kind)
    return (
        type_def is not None
        and type_def.semantic_category == GENERATED_ARTIFACT_CATEGORY
    )


def _dedupe_edges(edges: list[NormalizedEdge]) -> list[NormalizedEdge]:
    seen: set[tuple[str, str, str, str | None, bool]] = set()
    deduped: list[NormalizedEdge] = []
    for edge in edges:
        key = (
            edge.source_id,
            edge.target_id,
            edge.edge_type,
            edge.source_field,
            edge.authored,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(edge)
    return deduped
