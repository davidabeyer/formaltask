---
name: validating-task-plans
description: This skill should be used when validating batches of task specifications
  before creation. Activates when processing task plans from review findings, epic
  decompositions, or any batch task generation. Use when user says "validate task
  plan", "check these tasks", "are these tasks well-specified", or when --validate
  flag is passed to pm-review-fix. Ensures expert-planning quality standards, complete
  coverage, proper grouping, and priority preservation.
---

<role>
WHO: Task plan gatekeeper
ATTITUDE: Vague tasks create vague work. Reject early.
</role>

<purpose>
Your job is to catch bad task plans before they spawn bad work. 100% P0/P1 coverage required. Every task needs verb-first title, file:line references, and binary criteria.
</purpose>

## Quality Gates (BLOCKING)

| Gate | Threshold |
|------|-----------|
| P0/P1 Coverage | 100% |
| Task Quality | 100% pass |
| Priority Alignment | No demotions |
| Dependencies | No cycles |

---

## 6-Phase Validation

### Phase 1: Load Context

1. Read source document (review report, epic)
2. Count items needing tasks
3. Read generated task plan
4. Count proposed tasks

### Phase 2: Coverage Check

| Metric | Value |
|--------|-------|
| Source Items | {N} |
| Tasks Proposed | {N} |
| Coverage % | {N}% |

**Missing P0/P1 items = BLOCKING**

### Phase 3: Task Quality Matrix

| Task | Title | Files | Criteria | Size | Verdict |
|------|-------|-------|----------|------|---------|
| 1 | ✓/✗ | ✓/✗ | ✓/✗ | ✓/✗ | PASS/FAIL |

**Validation:**
| Criterion | Pass | Fail |
|-----------|------|------|
| Title | Verb-first, specific | Vague ("Fix bug") |
| Files | Has file:line | No references |
| Criteria | Binary, testable | Vague ("works") |
| Size | 30min-2hr | Too small/large |

### Phase 4: Grouping

- Same file + same category + <2hr = GROUP
- Different files + different concerns = SPLIT
- P0 and P2 in same task = SPLIT

### Phase 5: Priority Alignment

P0 → P1+ demotion = **BLOCKING**

### Phase 6: Dependencies

Circular dependencies = **BLOCKING**

---

## Output Format

```markdown
# Task Plan Validation Report

**Source:** {path}
**Tasks:** {count}

## Summary

| Check | Status |
|-------|--------|
| Coverage | PASS/FAIL |
| Task Quality | PASS/FAIL |
| Grouping | PASS/NEEDS WORK |
| Priority | PASS/FAIL |
| Dependencies | PASS/FAIL |

## Blocking Issues
1. {issue} - {fix}

## Verdict
**APPROVED** / **REVISE** / **REJECTED**

## Next Steps
- APPROVED → Proceed with task creation
- REVISE → Address blocking issues
- REJECTED → Re-run source analysis
```

---

## Auto-Reject Triggers

- P0 finding with no task
- P0 demoted to P2
- Circular dependencies
- Task with no acceptance criteria

## Auto-Revise Triggers

- Vague titles ("Fix bug")
- No file:line references
- >2hr task (needs split)
- <30min task (needs combine)

<rules>
- 100% P0/P1 coverage - no exceptions
- Verb-first titles - "Add X" not "X addition"
- file:line required - vague references are useless
- 30min-2hr sizing - split or combine outside this range
</rules>
