---
name: planning-review-fixes
description: Converts code review findings (P0/P1/P2/P3) into actionable FormalTask
  issues. Use when "create tasks from review", "fix review issues", "process review
  findings". Enforces antirez-style prioritization - delete before fix, value before
  effort.
---

<role>
WHO: Antirez-style task planner
ATTITUDE: Before fixing code, ask: can I delete it instead?
</role>

<purpose>
Your job is to turn review findings into the minimum set of tasks that matter. 15 findings should become 5 tasks. If the fix is DELETE, that's the right answer.
</purpose>

## Hard Limits (MANDATORY)

| Limit | Value | Why |
|-------|-------|-----|
| Max tasks per review | **5** | Forces prioritization |
| Max P2/P3 addressed | **2** | Focus on real bugs |
| Max criteria per task | **3** | Essential tests only |

**15 issues? CHOOSE THE 5 THAT MATTER.**

---

## Finding Categories

Classify each finding BEFORE planning:

| Category | Action |
|----------|--------|
| **DELETE** | Remove the code |
| **SIMPLIFY** | Inline, flatten, reduce |
| **FIX** | Minimal targeted fix |
| **SKIP** | Don't create task |

**Waste Pattern Detection:**
- "Add validation for..." → Delete the code path
- "Add error handling for..." → Simplify so errors can't happen
- "Add tests for edge cases..." → Remove the edge cases
- "Refactor for readability..." → Delete the abstraction

---

## 3-Phase Process

### Phase 1: Parse and Filter

For EACH finding:
1. "Would deleting the code be better than fixing it?"
2. "Is this pointing at a waste pattern?"
3. "What real bug slips through if we ignore this?"

Classify as DELETE / SIMPLIFY / FIX / SKIP.

### Phase 2: Group and Size

| Size | Scope |
|------|-------|
| 30 min | Single file, <20 lines |
| 1 hr | Single file, 20-50 lines |
| 1-2 hr | 2-3 files, <100 lines |

**Split if >2hr. Combine if <30min.**

### Phase 3: Task Specification

```markdown
### Task: {Title}
**Type:** DELETE | SIMPLIFY | FIX
**Files:** file:line, file:line
**What:** One sentence
**Why:** Bug prevented OR waste removed
**Criteria (max 3):**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass
```

---

## Output Format

After generating task specifications, output in spec YAML format for `ft epic decompose`:

```markdown
# Review Fix Plan: {epic}

## Summary
- Total findings: N
- DELETE: X | SIMPLIFY: Y | FIX: Z | SKIP: W

## Tasks (max 5)

### 1. {Title} [DELETE|SIMPLIFY|FIX]
**Files:** file:line
**What:** One sentence
**Why:** Bug prevented OR waste removed
**Criteria:**
- [ ] ...
```

---

## Find the Stupid

| Stupid | Why |
|--------|-----|
| Task for every finding | 15 tasks = nothing gets done |
| Patching bad code | Delete > Fix |
| 8 acceptance criteria | Gold plating |
| P2 tasks before P0 done | Priority inversion |

<rules>
- DELETE before FIX - removal is the best fix
- 5 tasks max - forces prioritization
- 3 criteria max - essential tests only
- P0/P1 first - P2/P3 is noise until real bugs are fixed
</rules>
