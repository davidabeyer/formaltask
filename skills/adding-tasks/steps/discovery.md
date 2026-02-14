---
consumes: [epic-context]
produces: [discovered-paths]
---
# Phase 2: Discovery

**BLOCKING GATE:** Epic validated in Phase 1.

## Search

```python
mcp__auggie-mcp__codebase-retrieval(
  information_request="Find code related to: {task_description}"
)
```

## Exit Criteria

At least 1 file path with line number. No paths found = search again with broader/different terms.
