---
consumes: [blocker-list]
produces: [applied-fixes]
---
# Phase 3: Apply Fixes

## PLAN fixes

Update plan.yaml in place (no new versions). Set resolution on history entries.

```python
import yaml

# Read current plan with inline history from /critique
plan_file = plans_dir / f"{project}-plan.yaml"
with open(plan_file) as f:
    plan = yaml.safe_load(f)

# For each goal, update history entries with resolution
for goal in plan.get("requirements", {}).get("goals", []):
    for history_entry in goal.get("history", []):
        # Find findings in this history entry that match our verified blockers
        for finding in history_entry.get("critique", {}).get("findings", []):
            finding_id = f"{finding['priority']}-{finding['finding'][:20]}"

            # Set resolution based on our Phase 2 verification
            if finding_id in valid_findings:
                finding["resolution"] = "fixed"  # We fixed it
            elif finding_id in invalid_findings:
                finding["resolution"] = "rejected"  # Critique was wrong
            elif finding_id in stale_findings:
                finding["resolution"] = "deferred"  # Already fixed or N/A

# Update goal.current if text was modified during fix
for goal in plan.get("requirements", {}).get("goals", []):
    if goal["id"] in updated_goals:
        goal["current"] = updated_goals[goal["id"]]

# Write updated plan
with open(plan_file, "w") as f:
    yaml.dump(plan, f, default_flow_style=False, sort_keys=False)
```

**Resolution values:**
- `fixed`: Finding was valid and addressed
- `rejected`: Finding was invalid (critique was wrong)
- `deferred`: Finding is stale or out of scope

## CriterionV2 history with resolution example

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
              resolution: "fixed"
```

## SPECS fixes

Update spec files in place. For EACH fix:
1. Read affected spec
2. Search ALL occurrences (including code examples)
3. Apply fix -- use Write for multi-fix files, Edit for single fixes
4. Document fix with finding ID

**EXIT CRITERIA:** All VALID P0+P1 fixes applied, resolution set on history entries.
