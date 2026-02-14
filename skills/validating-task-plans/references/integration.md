# Integration Guide

## Integration with pm-review-fix

When `--validate` flag is used:

```bash
/review-fix my-epic --dry-run --validate

# Flow:
# 1. Generate task plan (planning-review-fixes skill)
# 2. Spawn task-plan-validator agent
# 3. Agent validates using this skill's protocol
# 4. Output combined plan + validation report
# 5. If APPROVED, user can run without --dry-run
```

## Integration with Task Tool

When spawning validation agent:

```
Task(
  subagent_type="task-plan-validator",
  prompt="""
  Validate this task plan:

  Source: {review_report_path}

  Task Plan:
  {task_plan_content}

  Use the task-plan-validation skill protocol.
  Output a validation report with verdict.
  """
)
```

## Typical Workflow

1. Generate task plan via `pm-review-fix --dry-run`
2. Add `--validate` to spawn validator
3. Review validation report
4. If APPROVED, run without `--dry-run`
5. If REVISE, fix issues and re-validate
