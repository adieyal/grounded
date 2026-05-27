---
last_updated: 2026-05-27
---

# Verification Guidance

Use a project-owned `verification` spec when you need to check that modeled meaning exists in code, files, or generated outputs.

Rules:
- Put the check in a separate `verification` unit instead of overriding core renderer behavior.
- Keep the command focused on one concern when possible.
- Use multiple verification specs if the project needs multiple independent checks.
- Reference the verification from the relevant model unit or gap spec so the relationship is explicit.

Good uses:
- confirm a modeled field exists in source code
- confirm a generated artifact renders the expected section
- confirm a required configuration file or script is present

Example:
- If `REPORT-DOMAIN-003` models a structured report-analysis preview field, add a project verification spec such as `REPORT-VERIFY-002` with a command like `python scripts/check_report_fields.py` or `uv run python scripts/check_report_fields.py`.
- The verification should inspect the codebase for the expected field names or symbols and fail if the implementation drifts from the model.

Avoid:
- putting code-existence checks into page templates
- replacing the core Lattice verification command when the check is project-specific
- editing validation or rendering functions when a project-owned verification spec can express the check
- combining unrelated checks into one giant command unless they are inseparable
