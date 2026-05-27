from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Any

from .models import Spec
from .registry import SpecRegistry


ENTITY_KINDS = {
    "concept",
    "domain_object",
    "enum",
    "lifecycle_type",
    "lifecycle_value",
}


@dataclass(frozen=True)
class SearchRecord:
    id: str
    kind: str
    name: str
    description: str
    path: str
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    used_by: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    search_text: str = field(default="", repr=False)


@dataclass(frozen=True)
class SearchResult:
    score: int
    record: SearchRecord
    reason: str


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def tokens(value: str) -> set[str]:
    return {part for part in normalize(value).split() if part}


def build_search_records(registry: SpecRegistry) -> list[SearchRecord]:
    backlinks: dict[str, list[str]] = {spec.id: [] for spec in registry.active_specs}
    for spec in registry.active_specs:
        for reference in spec.references:
            if reference in backlinks:
                backlinks[reference].append(spec.id)

    return sorted(
        (_record_for_spec(spec, registry, backlinks) for spec in registry.active_specs),
        key=lambda record: (record.kind, record.id),
    )


def search_records(
    records: list[SearchRecord],
    query: str,
    *,
    kind: str | None = None,
    limit: int = 8,
) -> list[SearchResult]:
    scoped = filter_records(records, kind)
    results = [result for record in scoped if (result := score_record(query, record))]
    return sorted(results, key=lambda result: (-result.score, result.record.kind, result.record.id))[
        :limit
    ]


def filter_records(records: list[SearchRecord], kind: str | None) -> list[SearchRecord]:
    if kind is None or kind == "all":
        return records
    if kind in {"entity", "entities", "concept", "concepts"}:
        return [record for record in records if record.kind in ENTITY_KINDS]
    if kind in {"spec", "specs"}:
        return records
    return [record for record in records if record.kind == kind]


def score_record(query: str, record: SearchRecord) -> SearchResult | None:
    normalized_query = normalize(query)
    if not normalized_query:
        return None

    primary_names = (record.id, record.name)
    normalized_primary_names = [normalize(name) for name in primary_names if name]
    normalized_aliases = [normalize(alias) for alias in record.aliases if alias]
    normalized_names = [*normalized_primary_names, *normalized_aliases]
    query_tokens = tokens(normalized_query)
    record_tokens = tokens(record.search_text)

    if normalized_query in normalized_primary_names:
        return SearchResult(score=105, record=record, reason="exact id/name match")
    if normalized_query in normalized_aliases:
        return SearchResult(score=100, record=record, reason="exact alias match")
    if any(normalized_query in name for name in normalized_primary_names):
        return SearchResult(score=94, record=record, reason="id/name contains query")
    if any(normalized_query in alias for alias in normalized_aliases):
        return SearchResult(score=90, record=record, reason="alias contains query")
    if normalized_query in record.search_text:
        return SearchResult(score=82, record=record, reason="spec text contains query")

    overlap = query_tokens & record_tokens
    if overlap:
        coverage = len(overlap) / max(len(query_tokens), 1)
        return SearchResult(
            score=55 + round(25 * coverage),
            record=record,
            reason=f"token overlap: {', '.join(sorted(overlap))}",
        )

    best_ratio = max(
        (SequenceMatcher(None, normalized_query, name).ratio() for name in normalized_names),
        default=0.0,
    )
    if best_ratio >= 0.62:
        return SearchResult(
            score=round(45 + 30 * best_ratio),
            record=record,
            reason="fuzzy name match",
        )
    return None


def print_search_results(results: list[SearchResult]) -> int:
    if not results:
        print("No matches found.")
        return 1
    print(f"Found {len(results)} match{'es' if len(results) != 1 else ''}")
    for result in results:
        record = result.record
        print()
        print(f"{record.kind}: {record.name} ({result.score})")
        print(f"  id: {record.id}")
        print(f"  reason: {result.reason}")
        print(f"  path: {record.path}")
        if record.description:
            print(f"  description: {record.description}")
        if record.aliases:
            print(f"  aliases: {', '.join(record.aliases)}")
        if record.references:
            print(f"  references: {', '.join(record.references[:8])}")
        if record.used_by:
            print(f"  used_by: {', '.join(record.used_by[:8])}")
    return 0


def print_records(records: list[SearchRecord], *, verbose: bool = False) -> int:
    if not records:
        print("No records found.")
        return 1
    for record in records:
        print(f"{record.kind}: {record.name}")
        print(f"  id: {record.id}")
        print(f"  path: {record.path}")
        if record.description:
            print(f"  description: {record.description}")
        if record.references:
            print(f"  references: {', '.join(record.references[:8])}")
        if record.used_by:
            print(f"  used_by: {', '.join(record.used_by[:8])}")
        if record.tests:
            print(f"  tests: {', '.join(record.tests[:8])}")
        if verbose and record.aliases:
            print(f"  aliases: {', '.join(record.aliases)}")
    return 0


def records_json(records: list[SearchRecord]) -> str:
    return json.dumps([record_payload(record) for record in records], indent=2)


def results_json(results: list[SearchResult]) -> str:
    return json.dumps(
        [
            {"score": result.score, "reason": result.reason, **record_payload(result.record)}
            for result in results
        ],
        indent=2,
    )


def check_new_payload(
    records: list[SearchRecord],
    name: str,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    entity_matches = search_records(records, name, kind="entities", limit=limit)
    spec_matches = [
        result
        for result in search_records(records, name, kind="specs", limit=5)
        if result.record.kind not in ENTITY_KINDS and result.score >= 75
    ]
    high_confidence = [result for result in entity_matches if result.score >= 82]
    recommendation = (
        "Likely exists already; inspect the top entity before adding a new concept."
        if high_confidence
        else "No high-confidence entity match; inspect nearby matches and related specs before creating one."
    )
    return {
        "query": name,
        "recommendation": recommendation,
        "entity_matches": [
            {"score": result.score, "reason": result.reason, **record_payload(result.record)}
            for result in entity_matches
        ],
        "spec_matches": [
            {"score": result.score, "reason": result.reason, **record_payload(result.record)}
            for result in spec_matches
        ],
    }


def record_payload(record: SearchRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("search_text", None)
    return payload


def _record_for_spec(
    spec: Spec,
    registry: SpecRegistry,
    backlinks: dict[str, list[str]],
) -> SearchRecord:
    type_def = registry.type_definition_for(spec)
    aliases = _aliases_for(spec)
    text_parts = [
        spec.id,
        spec.kind,
        spec.display_name,
        spec.description,
        spec.statement,
        *aliases,
        *spec.tags,
        *spec.references,
        *spec.tests,
    ]
    if type_def is not None:
        for field_name in type_def.search_fields:
            text_parts.extend(_string_values(spec.data.get(field_name)))

    return SearchRecord(
        id=spec.id,
        kind=spec.kind,
        name=spec.display_name,
        description=spec.description,
        path=spec.path.as_posix(),
        aliases=aliases,
        tags=spec.tags,
        references=spec.references,
        used_by=tuple(sorted(backlinks.get(spec.id, ()))),
        tests=spec.tests,
        search_text=normalize(" ".join(text_parts)),
    )


def _aliases_for(spec: Spec) -> tuple[str, ...]:
    aliases: list[str] = []
    for key in ("aliases", "synonyms", "keywords"):
        aliases.extend(_string_values(spec.data.get(key)))
    for key in ("short_name", "name", "owner"):
        aliases.extend(_string_values(spec.data.get(key)))
    return tuple(dict.fromkeys(alias for alias in aliases if alias != spec.id))


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, list):
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    return ()
