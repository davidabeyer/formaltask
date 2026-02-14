---
consumes: []
produces: [portability-inventory]
---

# Discovery

Grep the target for hardcoded assumptions that break on other machines.

## Searches

```python
# Hardcoded paths
Grep(pattern="~/.claude|/home/\\w+|/Users/\\w+", output_mode="content")
Grep(pattern='["\']/[a-z]', glob="**/*.py", output_mode="content")

# Env var access
Grep(pattern="os\\.environ|os\\.getenv", output_mode="content")

# MCP/Claude Code specific
Grep(pattern="mcp__|call_mcp_tool|load_mcp_tools", output_mode="content")

# Infrastructure
Grep(pattern="tmux|sqlite3|WAL|\\.githooks", output_mode="content")
```

## Output

Write inventory to `00-inventory.md`:
- Path references (pattern, count, files)
- Env vars (var, required, default, documented)
- External deps (dep, type, fallback)

## Mode

**quick:** Quick grep, report findings inline. No file artifact.
**full:** Complete inventory written to `00-inventory.md`.

## Exit Criteria

Inventory complete.
