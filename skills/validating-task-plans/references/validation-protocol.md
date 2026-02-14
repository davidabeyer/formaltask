# Validation Protocol

Six-phase validation framework for task plan quality assurance.

## Phase 1: Load Context

```
1. Read the source document (review report, epic, etc.)
2. Count total items that need tasks
3. Read the generated task plan
4. Count tasks proposed
```

## Phase 2: Coverage Analysis

Verify every source item has a corresponding task:

```markdown
## Coverage Check

| Metric | Value |
|--------|-------|
| Source Items | {count} |
| Tasks Proposed | {count} |
| Items Addressed | {count} |
| Items Missing | {count} |
| Coverage % | {percentage} |

### Missing Items (BLOCKING if P0/P1)
- {source_item} - Not addressed

### Partially Addressed
- {source_item} - Mentioned but incomplete
```

**Quality Gate:** 100% P0/P1 coverage required. 90%+ P2 coverage recommended.

## Phase 3: Individual Task Quality

For each task, validate against expert-planning standards:

```markdown
## Task Quality Matrix

| Task | Title | Files | Criteria | Size | Verdict |
|------|-------|-------|----------|------|---------|
| 1 | check/x | check/x | check/x | check/x | PASS/FAIL |
| 2 | check/x | check/x | check/x | check/x | PASS/FAIL |
```

**Validation Criteria:**

| Criterion | Pass | Fail |
|-----------|------|------|
| Title | Verb-first, specific, scoped | Vague ("Fix bug", "Update code") |
| Files | Has file:line references | No file references |
| Criteria | Binary, testable, independent | Vague ("works", "no bugs") |
| Size | 30min-2hr estimate | <30min or >2hr |

## Phase 4: Grouping Validation

Check that related items are grouped appropriately:

```markdown
## Grouping Analysis

### Over-Grouped (SPLIT RECOMMENDED)
- Task {N}: {reason to split}

### Under-Grouped (COMBINE RECOMMENDED)
- Tasks {N} and {M}: {reason to combine}

### Grouping Verdict: OPTIMAL / NEEDS ADJUSTMENT
```

**Grouping Rules:**
- Same file + same category + <2hr combined = GROUP
- Different files + different concerns = SPLIT
- P0 and P2 in same task = SPLIT (priority mismatch)

## Phase 5: Priority Alignment

Verify source priorities are preserved:

```markdown
## Priority Alignment

| Source Priority | Task Priority | Status |
|-----------------|---------------|--------|
| P0 | P0 | Aligned |
| P0 | P1 | VIOLATION |
| P1 | P1 | Aligned |
```

**Quality Gate:** No P0 to P1+ demotions allowed.

## Phase 6: Dependency Validation

Check task dependencies are logical:

```markdown
## Dependency Check

### Valid Dependencies
- Task {N} -> Task {M}: {reason}

### Missing Dependencies
- Task {N} should depend on Task {M}: {reason}

### Circular Dependencies
- NONE / {describe cycle}
```
