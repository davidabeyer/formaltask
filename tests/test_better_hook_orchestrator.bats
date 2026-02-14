#!/usr/bin/env bats
# Tests for better-hook.sh orchestrator invocation on Stop event
# Task #1728

HOOK_SCRIPT="$HOME/.tmux/plugins/tmux-claude-status/hooks/better-hook.sh"

setup() {
    TEST_DIR=$(mktemp -d)

    # Mock the tmux commands
    export PATH="$TEST_DIR/bin:$PATH"
    mkdir -p "$TEST_DIR/bin"

    # Create mock tmux that returns a task session name
    cat > "$TEST_DIR/bin/tmux" << 'EOF'
#!/bin/bash
if [[ "$*" == *"display-message"* ]]; then
    echo "task-1234"
elif [[ "$*" == *"capture-pane"* ]]; then
    echo "Test output line"
fi
EOF
    chmod +x "$TEST_DIR/bin/tmux"

    # Create orchestrator invocation log
    ORCHESTRATOR_LOG="$TEST_DIR/orchestrator_invocations.log"
    export ORCHESTRATOR_LOG

    # Create mock Python that logs orchestrator calls with completion marker
    cat > "$TEST_DIR/bin/python3" << 'PYEOF'
#!/bin/bash
if [[ "$*" == *"-m hooks.lib.orchestrator"* ]]; then
    echo "$*" >> "$ORCHESTRATOR_LOG"
    touch "${ORCHESTRATOR_LOG}.done"
    exit 0
fi
exec /usr/bin/python3 "$@"
PYEOF
    chmod +x "$TEST_DIR/bin/python3"

    # Set up environment
    export TMUX="/tmp/tmux-test/default,1234,0"

    # Cache directory for tmux-claude-status
    mkdir -p "$HOME/.cache/tmux-claude-status"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# Helper: Wait for completion marker with timeout (deterministic, not flaky)
wait_for_orchestrator() {
    local timeout=${1:-20}  # 2 seconds max (20 * 0.1s)
    for i in $(seq 1 $timeout); do
        [ -f "${ORCHESTRATOR_LOG}.done" ] && return 0
        sleep 0.1
    done
    return 1  # Timeout
}

@test "Stop event invokes orchestrator when EFFECTIVE_TASK_ID is set" {
    STOP_JSON='{"event":"Stop","tool_name":"Bash"}'

    echo "$STOP_JSON" | "$HOOK_SCRIPT" Stop

    # Wait for orchestrator completion (deterministic, not flaky)
    wait_for_orchestrator

    # Verify orchestrator was called with correct arguments
    [ -f "$ORCHESTRATOR_LOG" ]
    grep -q "hooks.lib.orchestrator" "$ORCHESTRATOR_LOG"
    grep -q -- "--task-id 1234" "$ORCHESTRATOR_LOG"
    grep -q -- "--event Stop" "$ORCHESTRATOR_LOG"
    grep -q -- "--output" "$ORCHESTRATOR_LOG"
}

@test "Stop event does NOT invoke orchestrator without task ID" {
    # Override mock tmux to return non-task session
    cat > "$TEST_DIR/bin/tmux" << 'EOF'
#!/bin/bash
if [[ "$*" == *"display-message"* ]]; then
    echo "random-session"
elif [[ "$*" == *"capture-pane"* ]]; then
    echo "Test output"
fi
EOF
    chmod +x "$TEST_DIR/bin/tmux"

    STOP_JSON='{"event":"Stop","tool_name":"Bash"}'

    echo "$STOP_JSON" | "$HOOK_SCRIPT" Stop

    # Brief wait - if orchestrator isn't called by now, it won't be
    sleep 0.3

    # Orchestrator should NOT be called (no completion marker, no log)
    [ ! -f "${ORCHESTRATOR_LOG}.done" ]
    [ ! -f "$ORCHESTRATOR_LOG" ]
}

@test "Stop event preserves notification sound behavior" {
    # Create a mock afplay that logs it was called with completion marker
    SOUND_LOG="$TEST_DIR/sound.log"
    cat > "$TEST_DIR/bin/afplay" << 'EOF'
#!/bin/bash
echo "afplay called: $*" >> "$SOUND_LOG"
touch "${SOUND_LOG}.done"
EOF
    chmod +x "$TEST_DIR/bin/afplay"
    export SOUND_LOG

    STOP_JSON='{"event":"Stop","tool_name":"Bash"}'

    echo "$STOP_JSON" | "$HOOK_SCRIPT" Stop

    # Wait for sound command (deterministic polling)
    for i in $(seq 1 20); do
        [ -f "${SOUND_LOG}.done" ] && break
        sleep 0.1
    done

    # Verify sound command was called (notification not blocked by orchestrator)
    [ -f "$SOUND_LOG" ]
    grep -q "afplay" "$SOUND_LOG"
}

@test "SubagentStop event also invokes orchestrator (P2 coverage)" {
    # SubagentStop uses same case branch as Stop (line 106 of better-hook.sh)
    SUBAGENT_JSON='{"event":"SubagentStop","tool_name":"Task"}'

    echo "$SUBAGENT_JSON" | "$HOOK_SCRIPT" SubagentStop

    wait_for_orchestrator

    # Verify orchestrator was called for SubagentStop too
    [ -f "$ORCHESTRATOR_LOG" ]
    grep -q -- "--task-id 1234" "$ORCHESTRATOR_LOG"
    grep -q -- "--event Stop" "$ORCHESTRATOR_LOG"
}

@test "TASK_ID env var takes precedence over session name (P3 coverage)" {
    # Lines 116-117: $TASK_ID env var takes precedence over session name parsing
    export TASK_ID="9999"

    # Session name is task-1234 but TASK_ID=9999 should win
    STOP_JSON='{"event":"Stop","tool_name":"Bash"}'

    echo "$STOP_JSON" | "$HOOK_SCRIPT" Stop

    wait_for_orchestrator

    # Verify orchestrator used TASK_ID env var (9999), not session name (1234)
    [ -f "$ORCHESTRATOR_LOG" ]
    grep -q -- "--task-id 9999" "$ORCHESTRATOR_LOG"
    ! grep -q -- "--task-id 1234" "$ORCHESTRATOR_LOG"
}

@test "State file preserves orchestrator_session_id on update (Task #1796)" {
    # Task #1796: State file should merge, not replace, to preserve orchestrator fields
    STATE_FILE="$HOME/.cache/tmux-claude-status/1234-state.json"

    # Pre-populate with orchestrator_session_id
    mkdir -p "$(dirname "$STATE_FILE")"
    cat > "$STATE_FILE" << 'EOF'
{"schema_version":"1","task_id":"1234","phase":"ready","orchestrator_session_id":"test-uuid-12345"}
EOF

    STOP_JSON='{"event":"Stop","tool_name":"Bash"}'

    echo "$STOP_JSON" | "$HOOK_SCRIPT" Stop

    # Wait for hook to complete
    sleep 0.3

    # Verify orchestrator_session_id is preserved
    [ -f "$STATE_FILE" ]
    grep -q "orchestrator_session_id" "$STATE_FILE"
    grep -q "test-uuid-12345" "$STATE_FILE"
}

@test "State file preserves multiple orchestrator fields on update (Task #1796)" {
    # Test that all orchestrator-specific fields are preserved
    STATE_FILE="$HOME/.cache/tmux-claude-status/1234-state.json"

    # Pre-populate with multiple orchestrator fields
    mkdir -p "$(dirname "$STATE_FILE")"
    cat > "$STATE_FILE" << 'EOF'
{"schema_version":"1","task_id":"1234","phase":"working","orchestrator_session_id":"uuid-abc","handoff":{"phase":"blocked","summary":"needs review"},"reminder_count":2}
EOF

    STOP_JSON='{"event":"Stop","tool_name":"Bash"}'

    echo "$STOP_JSON" | "$HOOK_SCRIPT" Stop

    sleep 0.3

    # All preserved fields should exist
    [ -f "$STATE_FILE" ]
    grep -q "orchestrator_session_id" "$STATE_FILE"
    grep -q "uuid-abc" "$STATE_FILE"
    grep -q "handoff" "$STATE_FILE"
    grep -q "reminder_count" "$STATE_FILE"
    # Phase should be updated to "ready" (Stop event)
    # Note: jq outputs with spaces after colons, so use flexible pattern
    grep -q '"phase".*"ready"' "$STATE_FILE"
}
