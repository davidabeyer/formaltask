# Hook Input Analysis (Task #1698)

Analysis of Claude Code PreToolUse hook input based on 21 captured samples.

## Summary

The PreToolUse hook receives JSON input with a minimal, stable schema. Only two fields are required; Claude Code may add additional fields in the future.

## Schema

```python
from pydantic import BaseModel, ConfigDict

class PreToolUseHookData(BaseModel):
    """Schema for PreToolUse hook input data."""

    model_config = ConfigDict(extra="allow")

    tool_name: str      # Required: Name of the tool (e.g., "Bash", "Read")
    tool_input: dict    # Required: Tool-specific parameters
```

## Field Analysis

### Required Fields (present in ALL 21 samples)

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Name of the tool being invoked |
| `tool_input` | `dict` | Dictionary of tool-specific parameters |

### Optional Fields

No optional fields were observed across all 21 samples. The schema uses `extra="allow"` to accommodate any future fields Claude Code may add.

## Tool Types Observed

20 different tool types were captured:

| Tool | Sample Count | Example `tool_input` Fields |
|------|-------------|---------------------------|
| `Bash` | 2 | `command`, `timeout`, `description` |
| `Read` | 1 | `file_path`, `limit` |
| `Write` | 1 | `file_path`, `content` |
| `Edit` | 1 | `file_path`, `old_string`, `new_string` |
| `MultiEdit` | 1 | `file_path`, `edits[]` |
| `Glob` | 1 | `pattern`, `path` |
| `Grep` | 1 | `pattern`, `path`, `output_mode` |
| `TodoWrite` | 1 | `todos[]` |
| `WebFetch` | 1 | `url`, `prompt` |
| `WebSearch` | 1 | `query` |
| `Task` | 1 | `prompt`, `subagent_type`, `description` |
| `AskUserQuestion` | 1 | `questions[]` |
| `Skill` | 1 | `skill`, `args` |
| `NotebookEdit` | 1 | `notebook_path`, `new_source`, `cell_type` |
| `LSP` | 1 | `operation`, `filePath`, `line`, `character` |
| `EnterPlanMode` | 1 | (empty) |
| `ExitPlanMode` | 1 | (empty) |
| `KillShell` | 1 | `shell_id` |
| `TaskOutput` | 1 | `task_id`, `block` |
| `mcp__context7__get-library-docs` | 1 | `context7CompatibleLibraryID`, `topic` |

## Key Findings

1. **Minimal Schema**: Only `tool_name` and `tool_input` are guaranteed to be present
2. **Variable `tool_input`**: The structure of `tool_input` varies by tool type
3. **Empty `tool_input`**: Some tools (e.g., `EnterPlanMode`) have empty `tool_input` dicts
4. **MCP Tools**: MCP tool names follow the pattern `mcp__{server}__{tool_name}`
5. **Future-Proof**: Using `extra="allow"` ensures new fields won't break existing validators

## Usage in Validators

```python
from hooks.lib.hook_input_schema import PreToolUseHookData

# Parse and validate hook input
data = PreToolUseHookData.model_validate(hook_input)

# Access fields
tool_name = data.tool_name
command = data.tool_input.get("command", "")

# Extra fields accessible via model_extra
session_id = data.model_extra.get("session_id")
```

## Sample File Location

Raw samples stored at: `~/.claude/hook-input-samples.jsonl`

**Note**: This file may contain sensitive data and should NOT be committed to version control.

## Test Coverage

- 15 unit tests in `hooks/tests/unit/test_hook_input_analysis.py`
- Schema validates all 21 captured samples
- Tests cover parsing, field analysis, validation, and edge cases
