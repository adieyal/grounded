---
last_updated: 2026-05-24
---

# Slice Guidance

A slice is a bounded semantic view of the system being modeled.

Use a slice when you want to:
- model only part of a larger system
- group related units that belong together conceptually
- capture meaning that may be implicit in code rather than explicitly named
- create a reusable boundary for future expansion

Key properties:
- Slices can overlap.
- A slice can have a parent slice.
- A slice is not a partition of the system.
- A slice is about semantic grouping, not ownership of every concept in the repo.

How to use slices:
- start with the smallest coherent slice that answers the user’s goal
- include only the units that are necessary to explain and navigate that slice
- link member units back to the slice when membership is meaningful
- use parent slices when a narrower slice naturally sits inside a broader one

Good slice questions:
- What is the smallest coherent boundary that still makes sense on its own?
- What units belong together because they share meaning, not just implementation proximity?
- What should be explicit in the slice and what should remain out of scope?
- Does the slice need a parent to avoid duplicating broader context?

Avoid:
- turning slices into a full taxonomy of the repo
- using slices as a replacement for canonical ownership
- forcing disjoint grouping when the domain is naturally overlapping
- adding a slice just because a folder or module exists

When a slice is clear, model it as a reusable semantic boundary and keep the first pass small. Expand only after the user confirms the boundary is right.
