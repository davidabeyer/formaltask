---
consumes: [api-index]
produces: [oss-scorecard]
---

## Scorecard

**quick:** Rough grade (A-F) with blockers and quick wins inline. Skip detailed scorecard.

**full:** Weighted scorecard across 6 dimensions.

| Dimension | Weight |
|-----------|--------|
| API Design | 25% |
| Documentation | 20% |
| Security | 20% |
| Testing | 15% |
| Configuration | 10% |
| Distribution | 10% |

**Grades:** A (4.5-5), B (3.5-4.4), C (2.5-3.4), D (1.5-2.4), F (<1.5)

**Verdict:**
- **READY:** No blockers, score >= 3.5
- **CONDITIONAL:** No blockers, score 2.5-3.4
- **NOT READY:** Any blocker OR score < 2.5

**Severity:**

| Level | Meaning |
|-------|---------|
| Blocker | Cannot release: missing license, security vuln, broken install |
| Major | Should fix: missing main docs, no examples |
| Minor | Fix soon: API inconsistencies, edge case gaps |
| Polish | Nice to have: style preferences |

**EXIT CRITERIA:** Scorecard with verdict, severity-ranked findings, and actionable fixes.
