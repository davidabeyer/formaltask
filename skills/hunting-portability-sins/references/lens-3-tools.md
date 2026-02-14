# Lens 3: Tool Dependencies

Find assumptions about specific tools, Claude Code features, or shell environments.

## Search Patterns

```python
# MCP tool usage
Grep(pattern="mcp__|call_mcp_tool|load_mcp_tools", output_mode="content")

# Claude Code specific imports
Grep(pattern="from hooks\\.|import hooks\\.", output_mode="content")

# Subprocess calls
Grep(pattern="subprocess\\.(run|call|Popen|check_output)", output_mode="content")

# Shell-specific syntax in Python
Grep(pattern='shell=True.*".*\\|.*"', output_mode="content")

# Bash-specific features in scripts
Grep(pattern="\\[\\[|\\(\\(|declare|source", glob="**/*.sh", output_mode="content")
```

## Blocker Criteria

| Pattern | Severity | Rationale |
|---------|----------|-----------|
| MCP tool with no fallback | Blocker | Fails without Claude Code |
| Claude Code subagent assumption | Blocker | Task tool unavailable elsewhere |
| Bash-only syntax in shell scripts | Warning | Fails on POSIX sh |
| `shell=True` with complex pipes | Warning | Security and portability risk |
| Hardcoded tool paths (`/usr/bin/git`) | Warning | Different on various systems |

## Claude Code Specific Features

These ONLY work in Claude Code context:
- `Task()` subagent spawning
- `mcp__*` tool calls
- `Read()`, `Write()`, `Edit()` tools
- `AskUserQuestion()` interaction
- `Skill()` invocation

If code uses these, it must:
1. Have a non-Claude-Code execution path, OR
2. Clearly document Claude Code requirement

## Acceptable Patterns

```python
# Good: Optional MCP with fallback
try:
    from mcp_tools import call_mcp_tool
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

def search_code(pattern):
    if HAS_MCP:
        return call_mcp_tool("grep", pattern=pattern)
    else:
        return subprocess.run(["grep", "-r", pattern], capture_output=True)

# Good: POSIX-compatible scripts
#!/bin/sh
if [ -f "$FILE" ]; then  # Not [[ ]]
    echo "Found"
fi

# Good: Tool existence check
if shutil.which("git"):
    subprocess.run(["git", "status"])
else:
    print("Git not available")
```

## Shell Script Portability

| Bash-only | POSIX Alternative |
|-----------|-------------------|
| `[[ ]]` | `[ ]` with proper quoting |
| `(( ))` | `$((  ))` |
| `declare` | Variable assignment |
| `source` | `.` (dot) |
| `$RANDOM` | External random source |
| Arrays | Newline-separated strings |

## Output Fields

```json
{
  "id": "L3-001",
  "severity": "blocker",
  "category": "mcp_dependency",
  "tool": "mcp__morph-mcp__warpgrep_codebase_search",
  "location": {"file": "hooks/lib/search.py", "line": 89},
  "fallback_exists": false,
  "claude_code_only": true,
  "fix": "Add subprocess grep fallback or document Claude Code requirement"
}
```
