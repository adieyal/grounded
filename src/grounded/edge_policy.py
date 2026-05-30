from __future__ import annotations

EDGE_TYPES = (
    "mentions",
    "depends_on",
    "implements",
    "verified_by",
    "tests",
    "documents",
    "derives_from",
    "illustrated_by",
    "contains",
)

EDGE_TYPE_DESCRIPTIONS = {
    "mentions": "A weak reference or contextual mention; it does not prove trust.",
    "depends_on": "The source depends on the target as a prerequisite or lower/stabler dependency.",
    "implements": "The source implements the target behavior, contract, or rule.",
    "verified_by": "The source claim is verified by the target verification or test binding.",
    "tests": "The source test or proof mechanism exercises the target spec.",
    "documents": "The source generated artifact documents the target source spec.",
    "derives_from": "The source generated artifact or projection derives from the target source spec.",
    "illustrated_by": "The source spec is illustrated by the target governed asset.",
    "contains": "The source structural container contains the target member, document, section, or asset.",
}

SEMANTIC_LAYERS = (
    "primitive",
    "domain",
    "application",
    "interface",
    "infrastructure",
    "generated",
)

SEMANTIC_LAYER_ORDER = {layer: index for index, layer in enumerate(SEMANTIC_LAYERS)}

LEGACY_BACKLINK_FIELDS = ("used_by", "backlinks")


def is_allowed_edge_type(value: object) -> bool:
    return isinstance(value, str) and value in EDGE_TYPES


def is_allowed_semantic_layer(value: object) -> bool:
    return isinstance(value, str) and value in SEMANTIC_LAYERS
