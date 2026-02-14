---
consumes: [test-manifest]
produces: [audit-report]
---

**quick:** Audit tests yourself. Look for: no assertions, weak checks, mock abuse. Present findings inline by severity. Skip file artifacts.

**full:**
1. Read all batch JSON outputs
2. Dedupe overlapping findings
3. Sort by severity (P0 > P1 > P2 > P3)
4. Calculate overall health score

```markdown
# Test Suite Audit Report

## Summary
- Files: N | Tests: M | Score: X/100
- P0 (Critical): N | P1 (Major): M | P2: O | P3: P

## Priority Fixes
1. [P0] path/test.py:42 - No assertions in test_create
2. [P1] path/test.py:100 - Weak truthy check
...

## Health by Module
| Module | Files | Score | Top Issue |
|--------|-------|-------|-----------|

## Quick Wins
- [ ] Add assertion to test_basic (+10 score)
```

**EXIT CRITERIA:** Report delivered with actionable findings
