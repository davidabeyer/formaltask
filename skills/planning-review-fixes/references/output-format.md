# Output Format

## Full Task Plan Template

```markdown
# Review Fix Plan: {epic_name}

**Source Review:** {review_file_path}
**Review Date:** {date}
**Findings:** P0: {n}, P1: {n}, P2: {n}
**Tasks Created:** {total}

---

## Task Summary

| # | Title | Priority | Effort | Dependencies |
|---|-------|----------|--------|--------------|
| 1 | Fix path traversal in file operations | P0 | 1hr | None |
| 2 | Cache JSON serialization in prune loop | P0 | 30min | None |
| 3 | Add test coverage for pre_compact_worker | P0 | 2hr | None |

---

## Task Specifications

### Task 1: Fix path traversal vulnerability in file operations

{Full task specification per task-specification.md format}

### Task 2: ...

---

## Execution Order

### Phase 1: P0 Critical (Parallel)
- Task 1: Fix path traversal (no deps)
- Task 2: Cache JSON serialization (no deps)
- Task 3: Add test coverage (no deps)

### Phase 2: P1 High (After P0)
- Task 4: Refactor complex methods (depends on Task 1)
...

---

## Verification Checklist

- [ ] All P0 findings have corresponding tasks
- [ ] All P1 findings have corresponding tasks
- [ ] All tasks have file:line references
- [ ] All tasks have binary acceptance criteria
- [ ] All tasks are right-sized (30min - 2hr)
- [ ] Dependencies are mapped
- [ ] No orphaned findings
```

---

## Spec YAML Format

After generating the task plan, convert to spec YAML format:

```yaml
name: review-fix-plan
description: Tasks generated from code review findings

tasks:
  - title: Fix path traversal in file operations
    summary: Address P0 security vulnerability in file path handling
    acceptance_criteria:
      - {id: c-1, current: "Path validation added before file operations", history: []}
      - {id: c-2, current: "No directory traversal possible via user input", history: []}
      - {id: c-3, current: "Security test added", history: []}
    depends_on: []
    required_reviews:
      - code-quality
      - security
    spec_reference: specs/task-1-fix-path-traversal-spec.md

  - title: Cache JSON serialization in prune loop
    summary: Address P0 performance issue in prune worker
    acceptance_criteria:
      - {id: c-1, current: "JSON serialization cached outside loop", history: []}
      - {id: c-2, current: "Performance test verifies improvement", history: []}
    depends_on: []
    required_reviews:
      - code-quality
      - perf
    spec_reference: specs/task-2-cache-json-spec.md
```

---

## Integration with pm-task-add

After generating the task plan, create tasks using:

```bash
# For each task in the plan:
python3 -m hooks.cli.pm task-add {epic_name} "{task_title}" "{task_description}" \
  --criteria "{criterion_1}" \
  --criteria "{criterion_2}" \
  --criteria "{criterion_3}"
```

Or use `/task-add {epic_name}` interactively with the generated specifications.
