---
consumes: [validated-paths]
produces: [review-config]
---
# Phase 6: Determine Reviews & Doc Flag

**BLOCKING GATE:** Scope check passed in Phase 5.

## Review Types

Default: `code-quality`. Add others based on task domain (security, sqlite, perf, etc.).
See `formaltask/utils/schemas.py` REVIEW_TYPE_AGENTS for full list.

## Documentation Required

Set `documentation_required: true` if:
- Public API changes
- CLI command changes
- User-facing behavior changes

## Exit Criteria

Reviews list and doc flag determined.
