# 3-Phase Conversion Process

Execute ALL phases in order. Apply antirez lens throughout.

---

## Phase 1: Parse and Filter (Antirez Lens)

### 1.1 Extract Findings
```
Read review markdown (typically epic-reviews/{epic}-review-round-{N}.md)
Extract all findings with:
- File path and line number
- Priority (P0/P1/P2/P3)
- Category (security, performance, complexity, etc.)
- Description
```

### 1.2 Apply Deletion Test

**For EACH finding, ask these questions IN ORDER:**

```
1. Can we DELETE the code that has this problem?
   YES → Classify as DELETE

2. Can we SIMPLIFY so the problem disappears?
   YES → Classify as SIMPLIFY

3. Is this an actual bug that would affect users?
   YES → Classify as FIX

4. Otherwise → Classify as SKIP
```

### 1.3 Waste Pattern Detection

Check each finding against waste patterns:

| Finding Type | Likely Waste Pattern | Action |
|--------------|---------------------|--------|
| "Missing validation" | Code path shouldn't exist | DELETE |
| "Needs error handling" | Over-complex logic | SIMPLIFY |
| "Test coverage gap" | Untestable abstraction | DELETE abstraction |
| "Code duplication" | Premature extraction | INLINE instead |
| "Inconsistent naming" | Utils graveyard | IGNORE or inline |
| "Missing docstring" | P3 noise | SKIP |

### 1.4 Output: Filtered Inventory

```markdown
## Phase 1: Filtered Findings

### DELETE ({count})
| Finding | File:Line | Why delete > fix |
|---------|-----------|------------------|
| Missing validation in legacy_handler | foo.py:45 | Handler is unused |

### SIMPLIFY ({count})
| Finding | File:Line | Current → Target |
|---------|-----------|-----------------|
| Complex error handling | bar.py:120 | 5 try/except → 1 |

### FIX ({count})
| Finding | File:Line | Bug | Minimal Fix |
|---------|-----------|-----|-------------|
| SQL injection | auth.py:88 | User input in query | Parameterize |

### SKIP ({count})
| Finding | File:Line | Why skip |
|---------|-----------|----------|
| Missing docstring | utils.py:12 | P3, no bug |
```

---

## Phase 2: Group and Size

### 2.1 Grouping Rules

**GROUP IF:**
- Same file, within 50 lines, same category
- Different files, but single root cause
- One deletion removes multiple findings

**DO NOT GROUP IF:**
- Different priority levels (P0 + P2 = separate tasks)
- Would create task > 2 hours
- No logical relationship

### 2.2 Sizing Heuristics

| Indicator | Estimate |
|-----------|----------|
| Delete unused code | 30 min |
| Inline abstraction | 30-60 min |
| Single file fix, <20 lines | 30 min |
| Single file fix, 20-50 lines | 1 hr |
| 2-3 files, <100 lines | 1-2 hr |
| New test needed | Add 30 min |

### 2.3 Enforce Hard Limits

**Max 5 tasks.** If you have more:
1. Combine related DELETE findings
2. Combine related SIMPLIFY findings
3. Drop lowest priority FIX findings
4. Move remaining to "Future" section

### 2.4 Output: Task Groups

```markdown
## Phase 2: Task Groups

### Group 1: Delete Legacy Handlers [DELETE]
**Estimated:** 30 min
**Findings:** 3, 4, 7 (all become moot)
**Files:** handlers/legacy.py (entire file)

### Group 2: Simplify Parser [SIMPLIFY]
**Estimated:** 1 hr
**Findings:** 8, 9
**Files:** parser.py:100-200

### Group 3: Fix Auth SQL Injection [FIX]
**Estimated:** 30 min
**Findings:** 1
**Files:** auth.py:88
```

---

## Phase 3: Task Specification

### 3.1 Gather Context (Quick)

```python
# Only if needed - don't over-research
mcp__auggie-mcp__codebase-retrieval(
    information_request="Pattern for {fix type} in this codebase"
)
```

### 3.2 Write Minimal Specs

For each group:

```markdown
### Task: {Title}
**Type:** DELETE | SIMPLIFY | FIX
**Files:** {file:line, ...}
**What:** {One sentence - what changes}
**Why:** {One sentence - what bug prevented OR what waste removed}

**Acceptance (max 3):**
- [ ] {Specific observable criterion}
- [ ] {Specific observable criterion}
- [ ] All tests pass
```

### 3.3 Acceptance Criteria Rules

**Must be automatable:**
```markdown
# BAD (needs human)
- [ ] Code is cleaner
- [ ] Error handling improved

# GOOD (automatable)
- [ ] File handlers/legacy.py deleted
- [ ] grep -r "legacy_handler" returns 0 results
- [ ] auth.py uses db.execute(sql, params) not f-string
```

**Apply deletion test:**
> Would removing this criterion let a real bug slip through?
> NO → Don't include it

### 3.4 Final Output

```markdown
# Review Fix Plan: {epic}

## Summary
- Findings: {total}
- DELETE: {n} | SIMPLIFY: {n} | FIX: {n} | SKIP: {n}
- Tasks: {count} (max 5)

## Tasks

### 1. Delete Legacy Handlers [DELETE]
**Files:** handlers/legacy.py
**What:** Remove entire legacy handler module
**Why:** Unused since v2.0, source of 3 review findings

**Acceptance:**
- [ ] handlers/legacy.py deleted
- [ ] No imports of legacy_handler remain
- [ ] Tests pass

### 2. Fix Auth SQL Injection [FIX]
**Files:** auth.py:88
**What:** Use parameterized query instead of f-string
**Why:** P0 security vulnerability

**Acceptance:**
- [ ] auth.py:88 uses execute(sql, (param,)) not f"{sql}"
- [ ] bandit scan clean
- [ ] Tests pass

## Skipped (Future)
| Finding | Why Skipped |
|---------|-------------|
| Missing docstring foo.py:12 | P3, no bug |
```

---

## Checkpoint Questions

Before finalizing, verify:

- [ ] Did I try DELETE before FIX for each finding?
- [ ] Are there ≤5 tasks?
- [ ] Does each task have ≤3 acceptance criteria?
- [ ] Would antirez approve each task? (No gold plating?)
- [ ] Would deleting any criterion let a real bug through?
