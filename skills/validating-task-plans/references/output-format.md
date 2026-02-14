# Validation Report Output Format

Template for task plan validation reports.

## Report Template

```markdown
# Task Plan Validation Report

**Source:** {document_path}
**Tasks:** {count}
**Date:** {timestamp}

---

## Summary

| Check | Status | Notes |
|-------|--------|-------|
| Coverage | PASS/FAIL | {X}% covered |
| Task Quality | PASS/FAIL | {X}/{Y} tasks pass |
| Grouping | PASS/NEEDS WORK | {notes} |
| Priority | PASS/FAIL | {notes} |
| Dependencies | PASS/FAIL | {notes} |

---

## Blocking Issues (Must Fix)

1. {issue} - {fix}

## Recommended Fixes (Should Fix)

1. {issue} - {fix}

## Suggestions (Nice to Have)

1. {suggestion}

---

## Verdict

**APPROVED** / **REVISE** / **REJECTED**

{rationale}

---

## Next Steps

If APPROVED:
- Proceed with task creation
- Run: /review-fix {epic} (without --dry-run)

If REVISE:
- Address blocking issues
- Re-run validation

If REJECTED:
- Significant rework needed
- Consider re-running source analysis
```

## Verdict Guidelines

| Verdict | When to Use |
|---------|-------------|
| APPROVED | All blocking issues resolved, ready for creation |
| REVISE | Minor issues need fixing, re-run validation after |
| REJECTED | Significant rework needed, re-run source analysis |
