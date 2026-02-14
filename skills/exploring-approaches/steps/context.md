---
consumes: [requirements]
produces: [codebase-context]
---

## Phase 2: Context

**BLOCKING GATE:** Requirements clear.

**quick:** Use auggie directly for context. Skip subagent.

**full:** Spawn context gatherer:

```python
Task(
    subagent_type="Explore",
    model="haiku",
    description="Gather codebase context",
    prompt=f"Feature: {feature}. Find: similar patterns, reusable utilities, integration points. Write to {run.context} (under 300 words)"
)
```

**EXIT CRITERIA:** Context written. Wait before spawning explorers.
