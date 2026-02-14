---
consumes: [pass-findings, verified-findings]
produces: [style-report]
---
## Phase 7: Synthesize

**quick:** Present findings inline grouped by severity. Skip file artifacts.

**full:** Group verified findings:
1. **Hotspots** - Files with concentrated debt
2. **Quick wins** - Easy fixes, high impact
3. **Batch fixes** - Similar issues (all `d` -> `data`)

```markdown
# Style Audit: {module}

## Summary
- P0: N | P1: M | P2: O | P3: P

## Hotspots
{concentrated issues}

## Quick Wins
- [ ] Line 47: `d` -> `data`

## Batch Fixes
- 12 instances of `os.path` -> `pathlib`
```
