---
consumes: [user-request]
produces: [scope, project-name]
---
## Phase 0: Detect Scope

**quick:** Skip scoring, treat as MINI scope. Use auggie directly, no explorer subagent.

```python
from formaltask.skills import skill_init
from pathlib import Path
import os
import subprocess

description = "$ARGUMENTS".strip() if "$ARGUMENTS" else None

# Prompt for project name (short slug for directory, e.g., "installer", "auth-refactor")
AskUserQuestion(questions=[{
    "question": "Short project name for this plan? (e.g., 'installer', 'auth-refactor')",
    "header": "Project",
    "options": [{"label": "I'll type it", "description": "Short slug for .plans/{name}-plan.yaml"}],
    "multiSelect": False
}])
project = user_answer.lower().replace(" ", "-")

# Get project root (git root)
import subprocess
project_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True).stdout.strip())

init = skill_init("plan", project)
run = init["run"]
current_round = init["round"]
print(f"Round {current_round}")

# Git status check - run git fetch to ensure we're working with current state
subprocess.run(["git", "fetch", "--quiet"], capture_output=True)
ahead_behind = subprocess.run(
    ["git", "rev-list", "--left-right", "--count", "@{u}...HEAD"],
    capture_output=True, text=True
)
if ahead_behind.returncode == 0:
    behind, ahead = ahead_behind.stdout.strip().split()
    if int(behind) > 0:
        print(f"⚠️  Branch is {behind} commits behind upstream")
    if int(ahead) > 0:
        print(f"📤 Branch is {ahead} commits ahead of upstream")

status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
if status.stdout.strip():
    print(f"⚠️  Uncommitted changes: {len(status.stdout.strip().splitlines())} files")
```

**Scope question:**

```python
AskUserQuestion(questions=[{
    "question": "What's the scope of this work?",
    "header": "Scope",
    "options": [
        {"label": "Single task", "description": "One file, one feature, clear implementation → route to /task"},
        {"label": "Small project", "description": "2-5 files, some decisions to make → MINI planning"},
        {"label": "Multi-phase project", "description": "New module, architectural decisions, many files → FULL planning"}
    ],
    "multiSelect": False
}])

if scope == "Single task":
    print("Routing to /task")
    Skill("task", args=description)
    # STOP - /task handles it
```

| Scope | Mode | Behavior |
|-------|------|----------|
| Single task | — | Route to `/task`. **STOP** |
| Small project | MINI | No subagents, auggie-only discovery |
| Multi-phase | FULL | Spawn plan-explorer, full workflow |

**EXIT CRITERIA:** Scope confirmed by user, mode determined.
