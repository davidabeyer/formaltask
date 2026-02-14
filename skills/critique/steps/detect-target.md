---
consumes: [user-request]
produces: [target-type, target-paths]
---

# Phase 0: Detect Target

**quick:** Auto-detect target type. Skip to Phase 1.

**full:** Detect and validate target type:

```python
from pathlib import Path
import os

arg = "$ARGUMENTS".split()[0].strip() if "$ARGUMENTS" else None
args = "$ARGUMENTS"
skip_skeptic = "--skip-skeptic" in args
force_necessity = "--force-necessity" in args

home = Path(os.environ.get("HOME"))

# Get project root (git root)
import subprocess
project_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True).stdout.strip())

# Check if arg is a task artifact path (one-offs directory)
one_offs = home / "projects" / "one-offs"
if arg and (one_offs / arg / "task.md").exists():
    target_type = "TASK"
    task_artifact = one_offs / arg / "task.md"
elif arg and Path(arg).is_dir() and (Path(arg) / "task.md").exists():
    target_type = "TASK"
    task_artifact = Path(arg) / "task.md"
else:
    # Existing plan/spec detection - plans in .plans/ directory
    project = arg
    plans_dir = project_root / ".plans"
    spec_dir = plans_dir / f"{project}-specs"

    if spec_dir.exists() and list(spec_dir.glob("*-spec.yaml")):
        target_type = "SPECS"
    elif plans_dir.exists() and (plans_dir / f"{project}-plan.yaml").exists():
        target_type = "PLAN"
    else:
        target_type = None  # Tell user to run /plan or /task
```

| Target | Source |
|--------|--------|
| TASK | `~/projects/one-offs/{slug}/task.md` |
| SPECS | `.plans/{project}-specs/*-spec.yaml` |
| PLAN | `.plans/{project}-plan.yaml` |

**Done when:** Target type determined.
