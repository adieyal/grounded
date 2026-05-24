---
last_updated: 2026-05-24
---

# Tag Guidance

Tags are project-defined metadata that can be used to mark and browse knowledge units.

Rules:
- Tags are optional.
- Tags are not canonical identity.
- Tags are not modeled fields of the domain object.
- Field tags are allowed too, and should render on the field row rather than becoming parent-object fields.
- Tags may be overlapping and project-specific.
- Tag pages should group matching units by type when that makes scanning easier.
- Use tags for lightweight semantic flags such as deprecated or planned when the project defines the meaning.
- Tag links should point to generated tag pages, not to generic concept pages.

Good tag cases:
- feature lifecycle markers
- review or status flags
- project-specific grouping labels

Avoid:
- using tags as a replacement for canonical ownership
- using tags to encode structured domain data
- treating tags as a fixed global vocabulary unless the project explicitly defines one
