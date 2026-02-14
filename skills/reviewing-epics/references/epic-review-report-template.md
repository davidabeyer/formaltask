# Epic Review Report Template

```markdown
═══════════════════════════════════════════════════════════════════════════════
   EPIC REVIEW: {epic_name}
═══════════════════════════════════════════════════════════════════════════════

## Phase 1: Acceptance Criteria
Pass Rate: {pass_rate:.0%} {✅ if >= 80% else ❌}

## Phase 2: Quality Review
Verdict: {verdict}

Agents: {len(core_agents)} core + {len(specialists)} specialists

───────────────────────────────────────────────────────────────────────────────

## Findings by Task

{For each task:}
### Task #{task_id}: {title}

**AC Verification:** {passed}/{total} passed

**Quality Findings:**
{For each finding:}
- [{severity}] [{reviewer}] {file}:{line}
  {issue}
  **Fix:** {fix}

{If no findings: "No issues found."}

───────────────────────────────────────────────────────────────────────────────

## Summary

| Task | AC Pass | Blockers | High | Medium |
|------|---------|----------|------|--------|
{For each task:}
| #{task_id} | {ac_pass_rate} | {blockers} | {high} | {medium} |

**Totals:** {len(all_blockers)} blockers, {len(all_high)} high, {len(all_medium)} medium

## What's Good

{For each praise item:}
- ✅ Task #{task_id}: {what} - {why_good}

───────────────────────────────────────────────────────────────────────────────

## Next Steps

{If APPROVED:}
Ready to ship. No action required.

{If FIX_AND_SHIP:}
Fix blockers, then ship:
{For each blocker:}
- Task #{task_id}: {issue}

{If BLOCKED:}
Address {len(all_blockers)} blockers before proceeding.

═══════════════════════════════════════════════════════════════════════════════
```

## Verdict Rules

| Condition | Verdict |
|-----------|---------|
| 0 blockers | APPROVED |
| 1-2 blockers | FIX_AND_SHIP |
| 3+ blockers | BLOCKED |

## Phase 1 Gate

If AC pass rate < 80%, do NOT proceed to Phase 2.
Report failed criteria and exit.
