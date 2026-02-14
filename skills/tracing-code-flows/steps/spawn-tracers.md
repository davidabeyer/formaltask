---
consumes: [entry-points]
produces: [tracer-tasks]
---
# Phase 3: Launch Parallel Subagents (Full Only)

**Quick mode:** Skip this phase. Trace directly in Phase 5.

**Full mode:** ALL subagents launch in a SINGLE message. Sequential spawning is failure.

## Entry Point Tracers

```python
for i, ep in enumerate(entry_points, 1):
    Task(
        subagent_type="entry-point-tracer",
        description=f"Trace: {ep.name}",
        run_in_background=True,
        prompt=f"Read {run.handoffs}/entry-point-{i}.md. Trace all paths. Write Mermaid diagram to {run.outputs}/entry-point-{i}.md"
    )
```

## Gap Category Auditors

Each gap category maps to a specific subagent type:

| Gap Category | Subagent Type |
|--------------|---------------|
| error-handling | error-handling-reviewer |
| testing | test-quality-auditor |
| configuration | configuration-auditor |
| logging-monitoring | observability-auditor |
| migration-strategy | migration-auditor |

```python
gap_agents = {
    "error-handling": "error-handling-reviewer",
    "testing": "test-quality-auditor",
    "configuration": "configuration-auditor",
    "logging-monitoring": "observability-auditor",
    "migration-strategy": "migration-auditor"
}

for category in gap_categories:
    Task(
        subagent_type=gap_agents[category],
        description=f"Gap: {category}",
        run_in_background=True,
        prompt=f"Read {run.handoffs}/gap-{category}.md. Audit {category}. Write to {run.outputs}/gap-{category}.md"
    )
```

## Gap Categories by Mode

| Category | Quick | Standard | Deep |
|----------|-------|----------|------|
| Error Handling | Y | Y | Y |
| Testing | | Y | Y |
| Configuration | | Y | Y |
| Logging & Monitoring | | | Y |
| Migration Strategy | | | Y |
