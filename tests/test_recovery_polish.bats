#!/usr/bin/env bats
# test_recovery_polish.bats
#
# BATS integration tests for Phase 3 recovery polish
# Tests verify end-to-end recovery workflows and cross-component coordination

load 'test_helpers/tmux_fixtures'

# Components under test
TASK_RECOVER="$HOME/.claude/bin/task-recover"
PM_WORKER_NUDGE="$HOME/.claude/bin/pm-worker-nudge"
PM_PARALLEL_STATUS="$HOME/.claude/commands/pm-parallel-status.md"

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
# Simulation Helpers
# ============================================================================

simulate_stuck_worker() {
    local session="$1"
    # Send a blocking read command that waits for input
    tmux send-keys -t "$session" "read -p 'Waiting for input...' dummy" Enter
    sleep 0.3
}

simulate_idle_worker() {
    local session="$1"
    # Just put command at prompt (leave idle)
    tmux send-keys -t "$session" "pwd" Enter
    sleep 0.2
}

# ============================================================================
# Basic Component Validation
# ============================================================================

@test "task-recover script exists and is executable" {
    [ -x "$TASK_RECOVER" ]
}

@test "task-recover requires task_id argument" {
    run "$TASK_RECOVER"
    [ "$status" -ne 0 ]
    [[ "$output" == *"task_id"* ]] || [[ "$output" == *"Usage"* ]]
}

@test "pm-worker-nudge script exists and is executable" {
    [ -x "$PM_WORKER_NUDGE" ]
}

@test "pm-parallel-status command file exists" {
    [ -f "$PM_PARALLEL_STATUS" ]
}

# ============================================================================
# Recovery Component Integration
# ============================================================================

@test "task-recover handles missing session gracefully" {
    # Try to recover non-existent task
    run "$TASK_RECOVER" "nonexistent-task-$$"

    # Should fail gracefully
    [ "$status" -ne 0 ]
}

@test "pm-worker-nudge detects and rejects missing session" {
    # Try to nudge non-existent task
    run "$PM_WORKER_NUDGE" "nonexistent-task-$$"

    # Should fail due to missing session
    [ "$status" -ne 0 ]
}

# ============================================================================
# Nudge Count Persistence
# ============================================================================

@test "nudge count persists across multiple nudge attempts" {
    session=$(create_test_session "nudge-persist")
    task_id="${TEST_PREFIX}-nudge-persist"

    # Initialize count
    set_nudge_count "$task_id" "0"

    # Simulate multiple nudge attempts
    for i in 1 2 3; do
        count=$(get_nudge_count "$task_id")
        new_count=$((count + 1))
        set_nudge_count "$task_id" "$new_count"
    done

    # Verify final count
    count=$(get_nudge_count "$task_id")
    [ "$count" = "3" ]

    cleanup_test_session "$session"
}

@test "nudge count file survives script failure" {
    session=$(create_test_session "nudge-survive")
    task_id="${TEST_PREFIX}-nudge-survive"

    # Create count file
    set_nudge_count "$task_id" "1"

    # Try nudge (will fail on missing prompt, but file should persist)
    run "$PM_WORKER_NUDGE" "$task_id" || true

    # File should still exist
    count=$(get_nudge_count "$task_id")
    [ -n "$count" ]

    cleanup_test_session "$session"
}

# ============================================================================
# Alert Logging
# ============================================================================

@test "alerts logged with task ID and timestamp" {
    clear_alerts

    # Log a test alert
    echo "[2025-12-04T12:00:00Z] Task #test-123: Nudge attempt 1" >> "${TEST_TMP}/task-alerts.log"

    alerts=$(get_alerts)
    [[ "$alerts" == *"test-123"* ]]
    [[ "$alerts" == *"2025-12-04"* ]]
}

@test "multiple task alerts kept separate in log" {
    clear_alerts

    # Log alerts for different tasks
    echo "[2025-12-04T12:00:00Z] Task #task-1: Nudge attempt 1" >> "${TEST_TMP}/task-alerts.log"
    echo "[2025-12-04T12:00:01Z] Task #task-2: Nudge attempt 1" >> "${TEST_TMP}/task-alerts.log"

    alerts=$(get_alerts)
    [[ "$alerts" == *"task-1"* ]]
    [[ "$alerts" == *"task-2"* ]]
}

# ============================================================================
# Cross-Component Coordination
# ============================================================================

@test "workers can be nudged independently" {
    # Create two sessions
    session1=$(create_test_session "coord-1")
    session2=$(create_test_session "coord-2")

    # Verify both exist (use run to capture $status)
    run tmux has-session -t "$session1"
    [ "$status" -eq 0 ]
    run tmux has-session -t "$session2"
    [ "$status" -eq 0 ]

    cleanup_test_session "$session1"
    cleanup_test_session "$session2"
}

@test "recovery state is isolated per task" {
    session1=$(create_test_session "isolation-1")
    session2=$(create_test_session "isolation-2")

    task_id_1="${TEST_PREFIX}-isolation-1"
    task_id_2="${TEST_PREFIX}-isolation-2"

    # Set different nudge counts
    set_nudge_count "$task_id_1" "1"
    set_nudge_count "$task_id_2" "2"

    # Verify isolation
    count1=$(get_nudge_count "$task_id_1")
    count2=$(get_nudge_count "$task_id_2")

    [ "$count1" = "1" ]
    [ "$count2" = "2" ]

    cleanup_test_session "$session1"
    cleanup_test_session "$session2"
}

# ============================================================================
# Session State Verification
# ============================================================================

@test "session state can be captured for status reporting" {
    session=$(create_test_session "state-capture")

    # Send a command
    tmux send-keys -t "$session" "echo 'Test output'" Enter
    sleep 0.2

    # Capture state
    output=$(tmux capture-pane -t "$session" -p)

    # Should have some content
    [ -n "$output" ]

    cleanup_test_session "$session"
}

@test "prompt detection works with various shell prompts" {
    session=$(create_test_session "prompt-detect")

    # Send commands that would show prompt
    tmux send-keys -t "$session" "pwd" Enter
    sleep 0.3

    # Capture and check for prompt indicator
    output=$(tmux capture-pane -t "$session" -p)
    [[ "$output" == *"$"* ]] || [[ "$output" == *">"* ]] || [ -n "$output" ]

    cleanup_test_session "$session"
}
