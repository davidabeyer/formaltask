---
consumes: [tracer-outputs]
produces: [synthesis-report]
---
# Phase 5: Synthesize

## Quick Mode

Produce Mermaid diagram and findings inline. Present directly to user. No file output required.

## Full Mode

Build final report from collected subagent outputs.

### Report Components

1. **Executive summary** + risk assessment
2. **Architecture diagram** (Mermaid) -- top-level flow across components
3. **Entry point analyses** -- each with its own Mermaid diagram from subagent output
4. **Gap analysis by category** -- consolidated from gap subagent outputs
5. **Consolidated findings** -- prioritized P0 through P3
6. **Data flow diagram** (Mermaid) -- how data moves through the system

### Publish

```python
run.write_synthesis(final_report)
run.publish_report()
```

`synthesis.md` in the run directory is **REQUIRED** for contract validation. Do not skip this.
