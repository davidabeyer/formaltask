# Spec Validator Tool Requirements

## Tool Selection by Claim Type

| Claim Type | Primary Tool | Fallback |
|------------|--------------|----------|
| File path | Glob | Read (line verification) |
| Function/class | augment codebase-retrieval | Grep (exact match) |
| Pattern reference | augment → Read | warpgrep |
| Library feature | context7 | exa |
| API behavior | context7 → exa | WebFetch |

## Error Handling

- **Tool failure**: Log warning, mark claim as "unverified" (not P0)
- **Timeout**: Skip remaining validations for that task, continue others
- **No Spec content**: Skip task (some tasks may not have Specs)

## Blocking Behavior

- **P0 findings**: Block workflow (exit code 1)
- **P1 findings**: Warn but allow (exit code 0)
- **P2 findings**: Advisory only (exit code 0)

## Performance Guidelines

- Run file existence checks in parallel (multiple Glob calls)
- Cache library lookups (same library across multiple tasks)
- Limit semantic searches to 5 per task (avoid token exhaustion)
- Skip validation for tasks already marked completed/cancelled
