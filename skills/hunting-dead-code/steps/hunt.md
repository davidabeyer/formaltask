---
consumes: [hunt-target, code-topology]
produces: [hunt-findings]
fan_out: [import, function, branch, artifact]
---

# Phase 2: Hunt Dead Code

**quick:** Do single-pass yourself. Check imports, functions, branches, artifacts in sequence using grep/auggie. Report Kill/Suspect/Keep inline.

**full:** Spawn 4 parallel hunter subagents. Each hunter has a distinct territory.

```python
run.write_log("Spawning 4 parallel hunters", phase="Phase 2")

# All 4 Task calls in ONE message
Task(subagent_type="dead-code-import-hunter", run_in_background=True,
     prompt=f"Target: {target_path}\nTopology: {run.run_dir}/01-code-topology.md\nOutput: {run.outputs}/02-import-findings.md")
Task(subagent_type="dead-code-function-hunter", run_in_background=True,
     prompt=f"Target: {target_path}\nTopology: {run.run_dir}/01-code-topology.md\nOutput: {run.outputs}/02-function-findings.md")
Task(subagent_type="dead-code-branch-hunter", run_in_background=True,
     prompt=f"Target: {target_path}\nTopology: {run.run_dir}/01-code-topology.md\nOutput: {run.outputs}/02-branch-findings.md")
Task(subagent_type="dead-code-artifact-hunter", run_in_background=True,
     prompt=f"Target: {target_path}\nTopology: {run.run_dir}/01-code-topology.md\nOutput: {run.outputs}/02-artifact-findings.md")
```

Custom agents in `agents/dead-code/`.

```python
# After all hunters complete
run.write_log("All 4 hunters complete", phase="Phase 2")
```
