---
last_updated: 2026-05-24
---

# Modeling Guidance

Model stable meaning, not implementation noise.

Rules of thumb:
- keep metadata separate from modeled fields
- model only the concepts that should remain durable across code and docs
- use `short_name` or another display alias when the canonical name is too long for UI surfaces
- prefer one canonical owner per stable meaning
- choose the most specific existing type that fits
- use `schema_gap` when the current schema cannot express the fact cleanly
- keep links intentional and low-density

Good modeling questions:
- Is this a durable unit or just a display label?
- Would this still make sense if the implementation changed?
- Does this belong in the canonical model or in metadata around it?
- Can a future agent answer a real question from this unit?

Model shape guidance:
- `domain_object` and `business_entity` for durable nouns with structure and ownership
- `concept` for durable ideas, vocabulary, or explanation
- `workflow` for ordered behavior
- `business_rule` for invariants and policies
- `data_type` for reusable value shapes
- `example` for concrete proof points
- `schema_gap` for missing structure

If a concept is only useful for display, keep it as display metadata. If a field is only needed to render the page, do not promote it into the domain model unless it changes how the system is understood.
