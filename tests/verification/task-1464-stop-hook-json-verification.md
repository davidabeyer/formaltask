# Task #1464: Stop Hook JSON State Write Verification

**Date:** 2025-12-23T07:25:00Z
**Status:** COMPLETE

## Implementation

Added JSON state file writing to Stop hook in `~/.tmux/plugins/tmux-claude-status/hooks/better-hook.sh`.

### JSON Schema (v1)

```json
{
  "schema_version": "1",
  "task_id": "42" | null,
  "session_name": "task-42",
  "phase": "ready",
  "ts": "2025-12-23T07:25:00Z",
  "last_line": "What would you like to do next?"
}
```

### Key Features

1. **Task ID Resolution**:
   - Primary: `$TASK_ID` environment variable (set by Task #1462)
   - Fallback: Extract from session name (`task-42` → `42`)
   - Default: `null` if neither available

2. **Last Line Capture**:
   - Command: `tmux capture-pane -p -S - -E - -t "$TMUX_SESSION" | tail -1`
   - Sanitization: `tr -cd '[:print:]' | head -c 500`
   - Captures Claude's final output for state detection

3. **JSON Safety**:
   - Uses `jq` when available for proper escaping
   - Falls back to manual escaping (quotes, backslashes)

4. **Atomic Write**:
   - Uses `atomic_write()` from Task #1463
   - Temp file + mv pattern

### File Location

State files written to: `~/.cache/tmux-claude-status/{task_id or session_name}-state.json`

## Commit

- Repository: `~/.tmux/plugins/tmux-claude-status`
- Commit: `5e2ec23`

## Acceptance Criteria

- [x] JSON file written on Stop event with schema v1 format
- [x] last_line captured with `-S - -E -` flags
- [x] last_line sanitized (no control chars, max 500 chars)
- [x] TASK_ID included when available, null otherwise
- [x] File naming avoids `task-task-42` collision
