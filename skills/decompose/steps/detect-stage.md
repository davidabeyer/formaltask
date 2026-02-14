---
consumes: [user-request]
produces: [stage, project-paths]
---
# Phase 0: Detect Stage & Action

**quick:** Auto-detect stage and proceed to decomposition. Skip action question.

**full:** Detect stage and ask for action:

```python
from formaltask.skills import skill_init
from pathlib import Path
import os
import subprocess

project = "$ARGUMENTS".strip()
init = skill_init("decompose", project)
run = init["run"]

# Get project root (git root)
project_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True).stdout.strip())
plans_dir = project_root / ".plans"
spec_dir = plans_dir / f"{project}-specs"

has_specs = spec_dir.exists() and list(spec_dir.glob("*-spec.yaml"))
has_plan = (plans_dir / f"{project}-plan.yaml").exists()

if has_specs:
    stage = "SPECS_TO_TASKS"
elif has_plan:
    stage = "PLAN_TO_SPECS"
else:
    print(f"No plan found. Run: /plan {project}")
    return
```

```python
AskUserQuestion(questions=[{
    "question": f"Stage: {stage}. What action?",
    "header": "Action",
    "options": [
        {"label": "Decompose", "description": "Generate specs/tasks from plan"},
        {"label": "Critique", "description": "Validate existing specs before proceeding"}
    ],
    "multiSelect": False
}])
```

If **Critique** → `Skill("critique")` and stop.
If **Decompose** → continue to Phase 1.

**EXIT CRITERIA:** Action chosen.
