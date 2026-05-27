---
last_updated: 2026-05-24
---

# Type Selection Guidance

Use the most specific existing type that matches the stable meaning.

Heuristics:
- `domain_object`: durable noun with meaning, structure, and relationships.
- `business_entity`: concrete business-facing entity that carries fields and business meaning.
- `concept`: durable idea, rule-adjacent notion, or architectural vocabulary.
- `workflow`: ordered interaction or operating sequence.
- `business_rule`: invariant, policy, or must/never statement.
- `data_type`: reusable value shape or scalar meaning.
- `enum`: closed set of named values with explicit members.
- `example`: concrete instance that proves a rule or illustrates a concept.
- `schema_gap`: the current registry cannot express the fact cleanly.

Prefer:
- one unit per stable meaning
- no new type when an existing one already fits
- `schema_gap` instead of smuggling new semantics into prose

Do not introduce a new spec kind for tags. Tags are project-defined metadata that may drive tag pages or grouped navigation, but they are not a core unit type.

If a unit feels half-entity and half-concept, ask which part is actually stable and canonical before choosing the type.
