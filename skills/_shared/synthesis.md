---
consumes: [collected-findings]
produces: [synthesis]
optional: false
---
# Synthesis

Collect parallel results, merge into final report.

## Step 1: Deduplicate
Same finding from multiple sources = ONE finding with merged evidence.
- Keep the most specific description
- Combine evidence from all sources
- Use highest severity among duplicates

## Step 2: Pattern Group
Group findings by FIX PATTERN (not by source):
- Same fix across 5 instances = 1 finding with count: 5
- Different fixes = separate findings

## Step 3: Prioritize

| Priority | Criteria |
|----------|----------|
| P0 | Breaks functionality, security hole, data loss risk |
| P1 | Bug, incorrect behavior, missing validation |
| P2 | Style, performance, maintainability |
| P3 | Cosmetic, optional, preference |

## Step 4: Verdict
```
0 blockers (P0/P1) → APPROVED
1-2 fixable blockers → FIX_AND_SHIP
3+ blockers or fundamental flaw → REVISE
```

## Step 5: Report
Write to `synthesis.md` in the SkillRun directory:

```markdown
# {Title} — {VERDICT}

## Summary
{1-2 sentences: what was reviewed, overall health}

## Findings ({count})
### P0: {count}
- **[Pattern]** ({N} instances): {description}. Fix: {fix}.

### P1: {count}
...

## Next Step
{What to do based on verdict}
```