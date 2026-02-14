# Quality Gates and Anti-Patterns

## Quality Gates Summary

| Gate | Threshold | Blocking? |
|------|-----------|-----------|
| P0/P1 Coverage | 100% | YES |
| P2 Coverage | 90% | NO |
| Task Quality | 100% pass | YES |
| Grouping | No obvious issues | NO |
| Priority Alignment | No demotions | YES |
| Dependencies | No cycles | YES |

## Anti-Patterns to Flag

### Automatic REJECT

- P0 finding with no task
- P0 finding demoted to P2
- Circular dependencies
- Task with no acceptance criteria

### Automatic REVISE

- Vague task titles ("Fix bug")
- No file:line references
- >2hr task (needs split)
- <30min task (needs combine)

### Flag for Review

- P2 findings without tasks
- Aggressive grouping (>5 items per task)
- Aggressive splitting (1 item = 1 task always)

## Verification Checklist

Before issuing verdict:

- [ ] All P0 items have P0 tasks
- [ ] All P1 items have P1 tasks
- [ ] All tasks have verb-first titles
- [ ] All tasks have file:line references
- [ ] All tasks have binary criteria
- [ ] All tasks are 30min-2hr
- [ ] No circular dependencies
- [ ] Grouping is logical
- [ ] Report is complete and actionable
