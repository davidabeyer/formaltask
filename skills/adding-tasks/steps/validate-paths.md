---
consumes: [task-artifact]
produces: [validated-paths]
---
# Phase 3: Validate Paths (plan-explorer)

**BLOCKING GATE:** Discovery complete in Phase 2.

## Spawn plan-explorer agent

```python
Task(subagent_type="plan-explorer",
     description="Codebase discovery for task",
     prompt=f"""## TARGET
{discovered_paths}

## OUTPUT PATH
Return findings directly (no file output needed for validation)

## Task
Find evidence for: {task_description}
Validate paths listed above.
Return file:line citations, export inventories, importer traces.""")
```

**ABSOLUTE PATHS ONLY:** Use `/Users/...` in prompts, not `~/` or relative. Hooks enforce this.

## Exit Criteria

plan-explorer returned with file:line evidence. If paths invalid, loop back to Phase 2.
