---
consumes: [stage, project-paths]
produces: [codebase-context]
---
# Phase 1: Codebase Context

**quick:** Quick auggie check for relevant patterns. Skip warpgrep unless needed.

**full:** MANDATORY MCP context gathering:

```python
mcp__auggie-mcp__codebase-retrieval(
    information_request=f"Existing implementations related to: {plan_goal}. Find patterns, conventions."
)
mcp__morph-mcp__warpgrep_codebase_search(
    search_string=f"What modules will be affected by: {plan_goal}? What depends on them?",
    repo_path=project_root
)
```

**After MCP calls:** Verify that directories/files referenced in the plan still exist on disk. Plans from prior sessions go stale -- update spec content if paths are already deleted.

**EXIT CRITERIA:** MCP results captured AND plan claims verified against current disk state.
