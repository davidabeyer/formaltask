---
consumes: [user-request]
produces: [trace-config]
---
# Phase 0: Initialize

## Quick Mode

Skip SkillRun ceremony. Trace directly using auggie + warpgrep. No directory setup needed.

## Full Mode (Standard / Deep)

Initialize run directory:

```python
from formaltask.utils.skill_output import SkillRun

run = SkillRun.create("tracing-code-flows", f"Trace {target_name}")

# Structure:
# ~/projects/{project}/tracing-code-flows/
# |-- runs/{date}-trace-{slug}/
# |   |-- context.md      # Scope + entry point inventory
# |   |-- handoffs/       # Per-entry-point + per-gap-category
# |   |-- outputs/        # Subagent findings
# |   +-- synthesis.md    # Final report with diagrams
# +-- reports/
```

## Ask for Depth

| Mode | Subagents | Gap Categories |
|------|-----------|----------------|
| **Quick** | 1-3 | Error handling only |
| **Standard** | N+3 | Error, Testing, Config |
| **Deep** | N+5 | All 5 categories |

If the user didn't specify a mode, ask which they want before proceeding.
