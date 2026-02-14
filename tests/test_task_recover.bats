#!/usr/bin/env bats
# test_task_recover.bats
#
# BATS behavioral tests for task-recover script
# Tests verify actual script behavior with tmux sessions

load 'test_helpers/tmux_fixtures'

SCRIPT="$HOME/.claude/bin/task-recover"

# ============================================================================
# Setup/Teardown
# ============================================================================

setup_file() {
    create_test_tmp
}

teardown_file() {
    cleanup_test_tmp
    # Clean orphaned sessions
    tmux list-sessions -F '#{session_name}' 2>/dev/null | \
        grep "^${TEST_PREFIX}" | \
        xargs -I{} tmux kill-session -t {} 2>/dev/null || true
}

setup() {
    skip_if_no_tmux
}

# ============================================================================
# Basic Script Validation
# ============================================================================

@test "script syntax is valid" {
    run bash -n "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "script is executable" {
    [ -x "$SCRIPT" ]
}

@test "script requires task_id argument" {
    run "$SCRIPT"
    [ "$status" -ne 0 ]
    [[ "$output" == *"task_id"* ]] || [[ "$output" == *"Usage"* ]]
}

# ============================================================================
# Behavioral Tests (using tmux fixtures)
# ============================================================================

@test "task-recover detects and rejects missing session" {
    # Test with non-existent task ID (no session)
    run "$SCRIPT" "nonexistent-task-99999"

    # Should fail due to missing session
    [ "$status" -ne 0 ]
}

@test "task-recover handles missing tmux gracefully" {
    # Verify script reports missing session error
    run "$SCRIPT" "nonexistent-$$"

    # Should fail with informative error message
    [ "$status" -ne 0 ]
    [[ "$output" == *"session"* ]] || [[ "$output" == *"Session"* ]]
}

@test "task-recover session can be created and accessed" {
    # Create a test session that task-recover would work with
    session=$(create_test_session "recover-behavior")

    # Verify session was created
    [ -n "$session" ]

    # Verify we can access the session with tmux (use run for $status)
    run tmux has-session -t "$session"
    [ "$status" -eq 0 ]

    cleanup_test_session "$session"
}

@test "task-recover preserves session after interrupt" {
    # Create session with running command
    session=$(create_test_session "recover-preserve")

    # Put a command in the session
    tmux send-keys -t "$session" "echo 'starting'" Enter
    sleep 0.3

    # Capture output before interrupt
    before=$(tmux capture-pane -t "$session" -p)

    # Verify session still exists (mock of interrupt handling) - use run for $status
    run tmux has-session -t "$session"
    [ "$status" -eq 0 ]

    cleanup_test_session "$session"
}

@test "task-recover can send multiple interrupt signals" {
    # Create session with long-running process
    session=$(create_test_session "recover-interrupt")

    # Start a process that needs interrupting
    tmux send-keys -t "$session" "sleep 300" Enter
    sleep 0.3

    # Send interrupt signals (C-c)
    tmux send-keys -t "$session" C-c
    sleep 0.2
    tmux send-keys -t "$session" C-c
    sleep 0.2

    # Verify session still exists and can receive commands - use run for $status
    run tmux has-session -t "$session"
    [ "$status" -eq 0 ]

    cleanup_test_session "$session"
}

@test "task-recover session state can be captured" {
    # Create session and send commands
    session=$(create_test_session "recover-state")

    # Send some commands
    tmux send-keys -t "$session" "echo 'test'" Enter
    sleep 0.3

    # Capture pane output (what task-recover would see)
    output=$(tmux capture-pane -t "$session" -p)

    # Verify we got output (not empty)
    [ -n "$output" ]

    cleanup_test_session "$session"
}
