---
consumes: [portability-inventory]
produces: [portability-report]
---

# Report

**quick:** Present portability grade (A-F), blockers, and quick wins inline. No file artifacts.

**full:** Write report:

```markdown
# Portability Audit: {project}

## Summary
Grade: A-F | Blockers: N | Effort: X hours

## Critical Blockers
| Issue | Current | Fix | Effort |
|-------|---------|-----|--------|

## Quick Wins
Easy fixes, high impact

## Migration Guide
Step-by-step for new users
```

## Severity Reference

| Level | Criteria |
|-------|----------|
| Blocker | Code fails on first run |
| Warning | Feature broken, core works |
| Note | Suboptimal but functional |
