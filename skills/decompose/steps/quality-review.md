---
consumes: [spec-files, db-tasks, project-paths]
produces: [decompose-report]
---
# Phase 3: Quality Review + Phase 4: Output

## Phase 3: Quality Review (full only)

**quick:** Skip quality review. Go directly to output.

**full:** Spawn reviewer for PLAN_TO_SPECS:

```python
Task(subagent_type="spec-quality-reviewer",
     prompt=f"""Review specs in {spec_dir}/.
Checklist: 1) Each task PR-worthy 2) Criteria automatable 3) No circular deps
4) ≥50% tasks independent""")
```

**EXIT CRITERIA:** Reviewer returned with findings.

---

## Phase 4: Output

```python
run.publish_report(f"{project}-decomposition.md")
```

**PLAN_TO_SPECS:**
```
═══════════════════════════════════════════════════════════════
   ✓ DECOMPOSED: {project} (plan → specs)
═══════════════════════════════════════════════════════════════
Specs: {count}

Next: /critique {project}  (validate specs)
═══════════════════════════════════════════════════════════════
```

**SPECS_TO_TASKS:**
```
═══════════════════════════════════════════════════════════════
   ✓ DECOMPOSED: {project} (specs → tasks)
═══════════════════════════════════════════════════════════════
Tasks: {count}

Next: ft work spawn --epic {project}
═══════════════════════════════════════════════════════════════
```

**EXIT CRITERIA:** Summary displayed with next step.
