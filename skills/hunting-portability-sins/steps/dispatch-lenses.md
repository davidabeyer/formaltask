---
consumes: [portability-inventory]
produces: [lens-outputs]
optional: true
---

# Dispatch 8 Parallel Lenses

**quick:** Skip. Analyze portability issues yourself covering paths, env vars, tool deps, config. Report inline.

**full:** Spawn ALL 8 lens agents in ONE message.

```python
LENSES = [
    "portability-lens-paths",
    "portability-lens-env-vars",
    "portability-lens-tools",
    "portability-lens-infrastructure",
    "portability-lens-services",
    "portability-lens-filesystem",
    "portability-lens-config",
    "portability-lens-docs",
]

# ALL 8 in ONE message
for i, agent in enumerate(LENSES, 1):
    Task(
        subagent_type=agent,
        description=f"Lens: {agent.replace('portability-lens-', '')}",
        run_in_background=True,
        prompt=f"Inventory: 00-inventory.md | Output: lens-{i}.json"
    )
```

Each lens: max 3 blockers, 5 warnings, 5 skipped.

## Exit Criteria

All 8 lens outputs exist.
