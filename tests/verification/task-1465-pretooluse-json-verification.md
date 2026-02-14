# Task #1465: PreToolUse Hook JSON State Write Verification

**Date:** 2025-12-23T07:30:00Z
**Status:** COMPLETE

## Implementation

Added JSON state file writing to PreToolUse hook in `~/.tmux/plugins/tmux-claude-status/hooks/better-hook.sh`.

### JSON Schema (v1) - PreToolUse

```json
{
  "schema_version": "1",
  "task_id": "42" | null,
  "session_name": "task-42",
  "phase": "working",
  "ts": "2025-12-23T07:30:00Z",
  "tool": "Read"
}
```

### Key Features

1. **Tool Name Extraction**:
   - Pattern: `grep -o '"tool":"[^"]*"' | head -1 | cut -d'"' -f4`
   - Extracts tool name from Claude Code hook JSON input

2. **Task ID Resolution** (same as Stop hook):
   - Primary: `$TASK_ID` environment variable
   - Fallback: Extract from session name
   - Default: `null`

3. **Consistent Patterns**:
   - Same atomic_write() function
   - Same jq/manual JSON escaping
   - Same file naming convention

### State File Updates

PreToolUse writes `phase: "working"` + `tool` field:
- Dashboard sees worker is actively executing
- Orchestrator knows which tool is being used

Stop writes `phase: "ready"` + `last_line` field:
- Dashboard sees worker is idle
- Orchestrator sees Claude's final output

## Commit

- Repository: `~/.tmux/plugins/tmux-claude-status`
- Commit: `1a27fd0`

## Acceptance Criteria

- [x] JSON file written on PreToolUse event
- [x] tool field contains current tool name
- [x] phase is "working"
- [x] File naming consistent with Stop hook
