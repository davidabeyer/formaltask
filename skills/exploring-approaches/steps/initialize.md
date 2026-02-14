---
consumes: [real-decision]
produces: [skill-run]
---

## Phase 0: Initialize

**BLOCKING GATE:** Meta-analysis complete.

**quick:** Skip SkillRun. Explore approaches inline using auggie.

**full:** Initialize run directory:

```python
from formaltask.utils.skill_output import SkillRun

run = SkillRun.create("exploring-approaches", f"Explore {feature_name}")

# Structure:
# ~/projects/{project}/exploring-approaches/
# ├── runs/{date}-explore-{slug}/
# │   ├── context.md      # Codebase context
# │   ├── handoffs/       # Per-explorer instructions
# │   ├── outputs/        # Per-explorer findings
# │   └── synthesis.md    # Comparison
# └── reports/
```

**EXIT CRITERIA:** SkillRun created.
