---
consumes: [user-request]
produces: [critique-findings]
---
# Phase 0 + 0.5: Load Critique + Context Validation

## Phase 0: Load Critique

```python
from formaltask.skills import skill_init
from pathlib import Path
import yaml
import os
import subprocess

project = "$ARGUMENTS".strip() if "$ARGUMENTS" else None

init = skill_init("revise", project)
run = init["run"]
current_round = init["round"]
print(f"Round {current_round}")

# Get project root (git root)
project_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True).stdout.strip())
plans_dir = project_root / ".plans"
spec_dir = plans_dir / f"{project}-specs"
epic_dir = plans_dir / f"{project}-specs"  # epics in same dir as specs
```

Derive paths: `.plans/` -> `{project}-specs/`.

Read critique findings from plan.yaml (inline in goal history):

```python
# All critique data is inline in plan.yaml - no separate .md files
plan_file = plans_dir / f"{project}-plan.yaml"
with open(plan_file) as f:
    plan = yaml.safe_load(f)

# Detect target type from content
if spec_dir.exists() and list(spec_dir.glob("*-spec.yaml")):
    target_type = "SPECS"
else:
    target_type = "PLAN"

# Extract findings from goal history
all_findings = []
for goal in plan.get("requirements", {}).get("goals", []):
    goal_id = goal.get("id")
    for history_entry in goal.get("history", []):
        critique = history_entry.get("critique")
        if critique and critique.get("findings"):
            for finding in critique["findings"]:
                if finding.get("resolution") is None:  # Only unresolved findings
                    finding["goal_id"] = goal_id
                    all_findings.append(finding)

has_critique = len(all_findings) > 0
```

**EXIT CRITERIA:** Plan loaded, findings extracted from inline history, target type determined.

---

## Phase 0.5: Context Validation (BLOCKING)

**BEFORE proceeding to extract-blockers:**

1. Display: "Found {len(all_findings)} unresolved findings in plan.yaml. Is this the correct critique? [Y/n]"
2. Ask: "What is this revision's goal?"
   - **A) Patch findings** -- Fix specific critique issues in existing plan/specs
   - **B) Capture new proposal** -- Plan missed the point entirely

**If B:** Explain: "For new proposal capture, use `/plan` instead. `/revise` is for critique-based fixes."

**If user expresses frustration:** Explicitly acknowledge, then FOLLOW ALL PHASES. Frustration is not permission to shortcut -- shortcuts cause the failures that frustrate users.

**EXIT CRITERIA:** User confirmed findings and revision goal.
