---
name: implementing-review-feedback
description: Implements code review feedback systematically, then commits and pushes.
  Use when user provides reviewer comments, PR feedback, or code review notes. One
  item at a time, mark complete before moving on.
---

<role>
WHO: Review feedback executor
ATTITUDE: One feedback item at a time. Mark complete before moving on.
</role>

<purpose>
Your job is to implement review feedback systematically—no batching, no skipping. Each item gets done and marked complete before the next one starts.
</purpose>

## Workflow

### 1. Parse Reviewer Notes

- Split numbered lists and bullets
- Extract distinct change requests
- Clarify ambiguous items BEFORE starting

### 2. Create Todo List

Use `TodoWrite` for each feedback item:
- One todo per change
- Mark first as `in_progress` before starting
- Only ONE `in_progress` at any time

### 3. Implement Systematically

For each todo:

**Locate:**
- Grep for functions/classes
- Glob for files by pattern
- Read current implementation

**Change:**
- Use Edit tool
- Follow CLAUDE.md conventions
- Preserve existing functionality

**Verify:**
- Check syntax
- Run relevant tests
- Confirm reviewer's intent addressed

**Update:**
- Mark todo `completed` IMMEDIATELY
- Move to next (one `in_progress` only)

### 4. Validate

After all changes:
```bash
ruff check --fix && ruff format
pytest {affected_tests}
```

### 5. Commit and Push (if requested)

```bash
git add -A
git commit -m "fix: Address review feedback for task-{id}

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push
```

### 6. Task Completion (if --auto-complete)

```bash
# Without review bypass
ft task complete {task_id}

# With review bypass
ft task complete {task_id} --skip-review
```

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | Completed | Success |
| 1 | Blocked by reviews | Run required reviews |
| 2 | PR created, review started | Wait for review |

---

## Edge Cases

| Case | Action |
|------|--------|
| Conflicting feedback | Ask user for guidance |
| Breaking changes | Notify before implementing |
| Tests fail after changes | Fix before marking complete |
| Code doesn't exist | Ask for clarification |

---

## Find the Stupid

| Stupid | Why |
|--------|-----|
| Batching completions | Lose track of progress |
| Multiple in_progress | Confusion about what's active |
| Skipping validation | Breaks build |
| No TodoWrite | Progress invisible |

<rules>
- One in_progress at a time - never batch
- Mark complete IMMEDIATELY - don't wait
- Validate before commit - ruff + tests
- Ask for clarity on ambiguous feedback - don't guess
</rules>
