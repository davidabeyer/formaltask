---
consumes: [user-request]
produces: [scope-verdict]
---
# Phase 5: Scope Check

**BLOCKING GATE:** Title and criteria specified in Phase 4.

## Scope Table

| Question | Single Task | Use /plan |
|----------|-------------|-----------|
| Files to modify | 1-4 | 5+ |
| PR reviewer would say | "LGTM" | "Split this" |
| Design needed? | No | Yes |

## Mechanical Exception

Same pattern 10+ times (search-replace, deletions, renames) = stays single task. Different logic per file = NOT mechanical.

## Routing

If any column shows "Use /plan": stop and run `/plan {epic} "{title}"`.

## Exit Criteria

Scope confirmed as single task OR routed to /plan (STOP skill execution).
