# Task #1463: Atomic Write Function Verification

**Date:** 2025-12-23T07:15:00Z
**Status:** COMPLETE

## Implementation

Added `atomic_write()` function to `~/.tmux/plugins/tmux-claude-status/hooks/better-hook.sh`:

```bash
# Atomic write: write to temp file then move (mv is atomic on same filesystem)
# Usage: atomic_write "/path/to/file" "content"
# Task #1463: Enables crash-safe state file updates
atomic_write() {
    local target="$1"
    local content="$2"
    local tmp_file="${target}.tmp.$$"

    echo "$content" > "$tmp_file" && mv "$tmp_file" "$target"
}
```

## Design Rationale

- **Temp file naming**: Uses `${target}.tmp.$$` where `$$` is the process ID, avoiding collisions from concurrent hooks
- **Atomicity**: `mv` on same filesystem is atomic (POSIX guarantee)
- **Failure safety**: If process crashes during `echo`, temp file is orphaned but target is unchanged

## Usage

```bash
atomic_write "/path/to/state.json" '{"phase":"working","ts":"2025-12-23T07:15:00Z"}'
```

## Commit

- Repository: `~/.tmux/plugins/tmux-claude-status`
- Commit: `817df1e`

## Unblocks

- Task #1464: Add JSON state write to Stop hook
- Task #1465: Add JSON state write to PreToolUse hook
