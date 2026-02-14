---
consumes: [critique-findings]
produces: [blocker-list]
---
# Phase 1: Extract Blockers

Findings already extracted in load-critique from `all_findings`. Group by action: add missing content, correct wrong claims, simplify antirez violations, add undeclared dependencies, fix interface mismatches.

```python
# Group findings by priority
p0_findings = [f for f in all_findings if f["priority"] == "P0"]
p1_findings = [f for f in all_findings if f["priority"] == "P1"]

print(f"P0 blockers: {len(p0_findings)}")
print(f"P1 blockers: {len(p1_findings)}")

for finding in p0_findings + p1_findings:
    print(f"  [{finding['priority']}] {finding['finding']}")
    print(f"       Action: {finding['action']}")
    print(f"       Goal: {finding.get('goal_id', 'N/A')}")
```

**ALL P0s AND P1s are MANDATORY.** Partial fix = fail.

**EXIT CRITERIA:** Every P0/P1 finding extracted with fix action.
