---
consumes: [verified-findings, target-content]
produces: [critique-verdict]
---

# Phase 5-7: Synthesize, Update Goal History, Commit & Display

## Phase 5: Synthesize

**quick:** Present verdict with blockers inline. Group by pattern. State verdict and next step.

**full:** Aggregate **verified** blockers by **pattern** (not instance). Same fix pattern = 1 blocker with count. Discard INVALID claims.

Verdict: 0 blockers → APPROVED | 1-2 fixable → FIX_AND_SHIP | 3+ or fundamental → REVISE

**EXIT CRITERIA:** Verdict determined with blocker count.

---

## Phase 6: Update Goal History (PLAN target only)

**For PLAN target:** Append critique findings to each goal's history inline in plan.yaml.

```python
import yaml

# Read current plan - plans_dir already set in Phase 0
plan_file = plans_dir / f"{project}-plan.yaml"
with open(plan_file) as f:
    plan = yaml.safe_load(f)

# For each goal, append critique entry to history
for goal in plan.get("requirements", {}).get("goals", []):
    goal_id = goal.get("id")
    # Find findings related to this goal
    related_findings = [f for f in blockers if goal_id in f.get("goal_ids", [])]

    if related_findings or current_round > 1:
        history_entry = {
            "version": f"r{current_round}",
            "text": goal.get("current"),  # Capture current state
            "critique": {
                "verdict": verdict,
                "findings": [
                    {"priority": f["priority"], "finding": f["finding"], "action": f["action"]}
                    for f in related_findings
                ]
            }
        }
        goal["history"].append(history_entry)

# Write updated plan
with open(plan_file, "w") as f:
    yaml.dump(plan, f, default_flow_style=False, sort_keys=False)
```

**CriterionV2 history format example:**
```yaml
goals:
  - id: "g-1"
    current: "All CLI commands have --help documentation"
    history:
      - version: "r2"
        text: "All CLI commands have --help documentation"
        critique:
          verdict: "FIX_AND_SHIP"
          findings:
            - priority: "P1"
              finding: "Missing --help for 'spawn' command"
              action: "Add help text to spawn command"
```

---

## Phase 7: Commit & Display

**quick:** Display verdict inline with blockers and next step. Skip git commit.

**full:** Commit plan.yaml with inline critique history:

```python
# All critique data is now inline in plan.yaml - no separate .md files
# plans_dir already set in Phase 0 as project_root / ".plans"
plan_file = f"{project}-plan.yaml"

# Commit updated plan.yaml with inline history
Bash(command=f"cd {plans_dir} && git add {plan_file} && git commit -m 'critique: {project} round {current_round} - {verdict}'")
```

Display: `CRITIQUE: {project} ({verdict})` with round, target type, blocker count.

**Verdict routing (user confirmation):**

```python
if verdict == "APPROVED":
    print(f"✅ APPROVED")
    AskUserQuestion(questions=[{
        "question": "Plan approved. What next?",
        "header": "Next",
        "options": [
            {"label": "/decompose", "description": f"Generate specs from plan: /decompose {project}"},
            {"label": "ft epic decompose", "description": f"Commit existing specs to DB: ft epic decompose {project}"},
            {"label": "Done for now", "description": "Exit without further action"}
        ],
        "multiSelect": False
    }])
    # Execute based on user choice
elif verdict in ("FIX_AND_SHIP", "REVISE"):
    print(f"⚠️ {verdict}")
    AskUserQuestion(questions=[{
        "question": f"Verdict: {verdict}. Run /revise to fix blockers?",
        "header": "Action",
        "options": [
            {"label": "Yes, run /revise", "description": f"Fix blockers: /revise {project}"},
            {"label": "No, I'll fix manually", "description": "Exit critique, fix yourself"}
        ],
        "multiSelect": False
    }])
    # If user chooses /revise, execute then re-run critique
```

**EXIT CRITERIA:** Verdict displayed, user chose next action.
