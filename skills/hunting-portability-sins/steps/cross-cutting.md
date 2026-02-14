---
consumes: [lens-outputs]
produces: [cross-cutting-analysis]
optional: true
---

# Cross-Cutting Analysis

**quick:** Skip. No lens outputs to cross-reference.

**full:** Read all lens outputs. Identify:
1. **Systemic patterns** -- same root cause across lenses
2. **Cascade fixes** -- one change fixes multiple issues
3. **Prioritization** -- what blocks adoption first

| Pattern | Example | Impact |
|---------|---------|--------|
| Single Source | All paths from one base | Fix base, fix all |
| Missing Abstraction | Direct env access everywhere | Add config layer |
| Implicit Knowledge | Requires knowing internals | Document or remove |

Write analysis to `cross-cutting.md`.

## Exit Criteria

Cross-cutting analysis complete.
