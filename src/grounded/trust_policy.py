from __future__ import annotations


TRUST_STATUSES = (
    "verified",
    "checkable",
    "observed",
    "aspirational",
    "unknown",
)
TRUST_STATUS_DESCRIPTIONS = {
    "verified": "The claim has targeted executable verification and must pass grounded verify.",
    "checkable": "The claim is structurally checkable through verification, or records why it is not wired yet.",
    "observed": "The claim is based on cited observation, source references, or an explicit observed basis.",
    "aspirational": "The claim is proposed or future intent, not current truth.",
    "unknown": "No stronger credibility claim is made.",
}
SEMANTIC_CATEGORIES = (
    "authored_knowledge",
    "generated_artifact",
    "registry_infrastructure",
)
AUTHORED_KNOWLEDGE_CATEGORY = "authored_knowledge"
TRUTH_OWNING_TRUST_STATUSES = frozenset({"verified", "checkable", "observed"})
GENERATED_ARTIFACT_CATEGORY = "generated_artifact"
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


def is_allowed_semantic_category(category: str) -> bool:
    return category in SEMANTIC_CATEGORIES
