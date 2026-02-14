---
consumes: [target-content]
produces: [regression-findings]
---

# Phase 2: Check Regression (Round 2+ only)

**quick:** Skip regression check.

**full:** Spawn `spec-regression-checker` (sonnet) → verify previous P0 blockers were fixed → write to `{outputs}/regression.md`.

**EXIT CRITERIA:** (Round 2+) Previous blockers verified as fixed or still present. (Round 1) Skip.
