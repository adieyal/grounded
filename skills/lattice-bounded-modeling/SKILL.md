---
name: lattice-bounded-modeling
description: Use when introducing Lattice into an existing codebase, defining only a subset of the system to model, or helping a user bound, type, and interlink a coherent slice before expanding further.
last_updated: 2026-05-24
---

# Lattice Bounded Modeling

Use this skill when the user wants Lattice to model a subset of a system rather than the whole codebase. The goal is to help the user and the LLM agree on a small, coherent slice, then turn that slice into canonical Lattice units with stable links.

This skill is the canonical workflow for:
- interactive scope definition
- subset-first Lattice bootstrapping in existing codebases
- choosing the right unit kinds and granularity
- connecting new units back to canonical owners without duplication
- rendering canonical owners with `lattice-link`, including inline prose links when a unit or goal is mentioned in a sentence

## Canonical Lattice Owners

- [PROJECT-CONCEPT-002](../../lattice/specs/concepts/PROJECT-CONCEPT-002.json): bounded modeling slice
- [PROJECT-WORKFLOW-001](../../lattice/specs/workflows/PROJECT-WORKFLOW-001.json): scope a bounded Lattice model

## Use This Skill When

- the user says they do not want to model the whole system
- Lattice is being introduced into an existing repo
- the first pass should focus on a single feature, workflow, bounded context, or concept cluster
- the agent needs to ask questions to determine the right modeling boundary
- the current shape of the domain is unclear and needs evidence-backed narrowing

## Non-Negotiables

- Model the smallest coherent slice that satisfies the user goal.
- Ask before assuming scope when the boundary is not explicit.
- Treat bootstrap requests as scoping-only until the user confirms the boundary.
- Do not edit code, specs, tests, or generated artifacts before confirmation.
- Do not move past the question ladder into implementation planning without explicit user confirmation.
- Do not inspect implementation more deeply than needed to frame the scoping questions.
- Prefer canonical owners over duplicated concepts or near-synonyms.
- Choose the most specific existing type that fits the meaning.
- Use `schema_gap` when the current registry cannot express the fact cleanly.
- Keep interlinks intentional: every reference should explain ownership, constraint, example, or dependency.
- Do not turn the first pass into a full-system inventory.

## Workflow

### 1. Open with a short plan

Before asking detailed questions, give the user a short plan that says:
- what slice you think we are scoping
- what evidence you will inspect
- how you will decide whether the slice is too broad
- when you will pause for confirmation

Keep the plan short enough that the user can correct it immediately.

### 2. Run the question ladder

Ask the user for the minimum information needed to bound the work:
- what outcome they want from the model
- what slice or subsystem they want to focus on
- what comparison or baseline relationship matters, if any
- what kind of deeper analysis they want the model to support
- what must stay out of scope
- what should happen when evidence is incomplete or not comparable

Keep the questions narrow and sequential. Prefer one question at a time unless the user has already given enough detail.

Important: the question ladder is the whole first pass. Do not draft the model, inspect deep implementation details, or propose changes until the user has answered enough to freeze the slice.

### 3. Anchor the slice in evidence

Use repo evidence to ground the model:
- inspect only the minimal code paths, docs, tests, and names needed to understand the requested slice
- collect the nouns, workflows, rules, and data shapes that repeat
- separate stable domain meaning from implementation detail

If the evidence suggests the slice is too broad, pause and narrow it before modeling further.

### 4. Propose the minimal canonical set

Draft the first model as a small set of linked units:
- `domain_object` or `business_entity` for durable nouns with ownership and structure
- `concept` for durable ideas, architectural notions, or explanatory vocabulary
- `workflow` for ordered behavior or user/system interaction
- `business_rule` for invariants, policies, and must/never statements
- `data_type` for reusable value shapes and scalar semantics
- `example` for concrete proof points
- `schema_gap` when the registry cannot express the fact cleanly

Prefer one unit per distinct durable idea. Do not split a concept just to create more files.

### 5. Choose the right granularity

Use the following tests:
- If the unit can be named in one sentence and owned by one source, it is probably a good candidate.
- If the unit is only a field, flag, or transient implementation detail, do not model it yet.
- If two names mean the same thing, keep one canonical owner and treat the other as an alias or reference.
- If a unit needs three or more caveats to make sense, the slice is probably too large.

### 6. Interlink deliberately

Build a small graph, not a mesh:
- link rules to the concepts or entities they constrain
- link examples to the rules they demonstrate
- link derived or specialized units back to their canonical parent
- link only when the relation helps a future reader answer a real question

Avoid duplicate ownership and avoid “just in case” links.

When referring to a canonical unit in prose, prefer an inline `lattice-link` over a bare ID. Use the short display label when it improves readability, and keep the canonical ID as the actual target. If the sentence is about a goal, rule, workflow, or owner, link the relevant canonical unit on first mention rather than collecting the links at the end.

### 6b. Model deliberately

Model stable meaning, not implementation noise:
- keep metadata separate from modeled fields
- use `short_name` or a display alias when the canonical name is too long for links or navigation
- model durable nouns as `domain_object` or `business_entity` only when they have ownership and structure worth preserving
- model durable ideas, policies, and explanatory vocabulary as `concept` or `business_rule`
- model repeatable value shapes as `data_type`
- model ordered behavior as `workflow`
- use `schema_gap` when the current registry cannot express the fact cleanly

If a concept is only useful as a presentation label, do not force it into a domain object. If a field is only operational metadata, do not elevate it into the core model just because the renderer can show it.

### 7. Refine interactively

After the first draft, show the user:
- the current in-scope boundary
- the units you would create or update
- the out-of-scope areas you are intentionally leaving alone
- the open questions that still block confident modeling

Then ask what should change before writing the next pass.

### 8. Freeze the slice

Once the user agrees:
- restate the final scope in plain language
- name the canonical units that own it
- note any deliberate exclusions
- proceed to implementation or spec updates

If the user has not confirmed the slice, stop after the question ladder and return the plan/questions only.

## Default Template

Start with the default modeling template for ordinary units and interactions. Override the concept pages below only when the default flow is too generic for the current slice.

### Override Pages

- [First response shape](./references/first-response.md)
- [Question ladder](./references/question-ladder.md)
- [Default modeling flow](./references/default-flow.md)
- [Scope boundary guidance](./references/scoping-boundary.md)
- [Type selection guidance](./references/type-selection.md)
- [Interlinking guidance](./references/interlinking.md)
- [Link rendering guidance](./references/link-rendering.md)
- [Modeling guidance](./references/modeling-guidance.md)
- [Slice guidance](./references/slices.md)
- [Short name guidance](./references/short-names.md)
- [Template override notes](./references/template-overrides.md)

## Special Cases

- Existing codebase: model from observed names and behavior first, not from aspirational architecture language.
- Hidden complexity: if the requested slice reveals an essential adjacent concept, call it out and ask whether it belongs in the slice.
- New subsystem introduction: anchor the model around user-visible workflows or public interfaces before drilling into internals.
- Overlapping terminology: keep one canonical term and map alternatives back to it.
