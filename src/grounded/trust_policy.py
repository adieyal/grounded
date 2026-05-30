from __future__ import annotations


TRUST_STATUSES = (
    "verified",
    "checkable",
    "observed",
    "aspirational",
    "unknown",
)
CLAIM_BEARING_KINDS = frozenset(
    {
        "business_rule",
        "concept",
        "decision",
        "domain_object",
        "enum",
        "example",
        "guardrail",
        "schema_gap",
        "verification",
        "workflow",
    }
)


def is_claim_bearing_kind(kind: str) -> bool:
    return kind in CLAIM_BEARING_KINDS
