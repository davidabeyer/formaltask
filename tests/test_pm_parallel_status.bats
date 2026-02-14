#!/usr/bin/env bats
# test_pm_parallel_status.bats
#
# BATS tests for pm-parallel-status health classification

# The actual command file is in user's ~/.claude/commands/, not project-level
COMMAND_FILE="$HOME/.claude/commands/pm-parallel-status.md"

@test "command file exists" {
    [ -f "$COMMAND_FILE" ]
}

@test "command uses classify_output from worker_monitor" {
    grep -q "classify_output" "$COMMAND_FILE"
}

@test "command uses base64 encoding for safe output passing" {
    grep -q "base64" "$COMMAND_FILE"
}

@test "command has health emoji mapping function" {
    grep -q "get_health_emoji" "$COMMAND_FILE"
}

@test "command uses tmux capture-pane for output" {
    grep -q "capture-pane" "$COMMAND_FILE"
}

@test "command has blocked workers detection" {
    grep -q "blocked.*emoji\|blocked.*section\|BLOCKED WORKERS\|detect.*blocked" "$COMMAND_FILE"
}

@test "command includes blocked workers summary" {
    grep -q "BLOCKED WORKERS\|blocked.*summary" "$COMMAND_FILE"
}

@test "shows nudge count from file" {
    grep -q "nudge-count\|nudge_count" "$COMMAND_FILE"
}

@test "shows recovering status indicator" {
    grep -qE "Recovering|recovering|🔧" "$COMMAND_FILE"
}
