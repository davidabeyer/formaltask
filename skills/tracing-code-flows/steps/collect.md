---
consumes: [tracer-tasks]
produces: [tracer-outputs]
---
# Phase 4: Collect Outputs (Full Only)

**Quick mode:** Skip this phase.

**Full mode:** Wait for all subagents to complete, then collect.

## Read All Outputs

```python
all_outputs = run.read_all_outputs()

entry_point_results = [f for f in all_outputs if f.startswith("entry-point-")]
gap_results = [f for f in all_outputs if f.startswith("gap-")]
```

## Verify Completeness

Check that every expected output file exists:
- One `entry-point-{i}.md` per entry point
- One `gap-{category}.md` per gap category in scope

If any output is missing, note it as a gap in the synthesis.
