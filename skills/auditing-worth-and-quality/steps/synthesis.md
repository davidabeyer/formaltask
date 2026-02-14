---
consumes: [verified-findings]
produces: [audit-synthesis]
---

**quick:** Present findings inline with function breakdown table.

**full:** Write to `synthesis.md`:

```markdown
## Audit: {file_path}
**LOC:** {count} | **Verdict:** [Delete file | Major refactor | Simplify | Keep]

### Function Breakdown
| Function | LOC | Verdict | Evidence | Quality |

### Dead Code (VERIFIED)
{grep evidence}

### Recommended Actions
1. {action with LOC impact}
```
