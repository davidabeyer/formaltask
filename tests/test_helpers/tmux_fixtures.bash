#!/usr/bin/env bash
# tests/test_helpers/tmux_fixtures.bash
#
# Shared test fixtures for tmux-based behavioral tests
# Provides: CI skip guards, session management, file isolation, cleanup
#
# Usage in test files:
#   load 'test_helpers/tmux_fixtures'
#
#   setup_file() { create_test_tmp }
#   teardown_file() { cleanup_test_tmp }
#   setup() { skip_if_no_tmux }

# ============================================================================
# CI Skip Guards
# ============================================================================

# Skip test if tmux not available (typically in CI)
skip_if_no_tmux() {
    if ! command -v tmux &>/dev/null; then
        skip "tmux not available"
    fi
    if [ -n "${CI:-}" ] && [ -z "${TMUX_TESTS_ENABLED:-}" ]; then
        skip "tmux tests disabled in CI (set TMUX_TESTS_ENABLED=1 to enable)"
    fi
}

# ============================================================================
# Test Isolation
# ============================================================================

# Generate unique prefix for this test run (use BASHPID for stable value in subshells)
# Format: bats-<pid>-<timestamp>
# Note: We compute this once at load time and export it
if [ -z "${TEST_PREFIX:-}" ]; then
    export TEST_PREFIX="bats-${BASHPID:-$$}-$(date +%s)"
fi

# Use BATS_FILE_TMPDIR if available (stable across tests), fallback to custom
# BATS_FILE_TMPDIR is set by BATS and persists for all tests in a file
export TEST_TMP="${BATS_FILE_TMPDIR:-/tmp/${TEST_PREFIX}}"

# ============================================================================
# Session Management
# ============================================================================

# Create a new tmux session with unique name
# Usage: SESSION=$(create_test_session "name")
create_test_session() {
    local suffix="${1:-test}"
    local session_name="${TEST_PREFIX}-${suffix}"

    # Create session with standard dimensions
    tmux new-session -d -s "$session_name" -x 80 -y 24

    # Return the full session name
    echo "$session_name"
}

# Kill a tmux session by name
# Usage: cleanup_test_session "$SESSION_NAME"
cleanup_test_session() {
    local session_name="$1"

    if [ -z "$session_name" ]; then
        return 0
    fi

    # Kill session, ignore errors if session doesn't exist
    tmux kill-session -t "$session_name" 2>/dev/null || true
}

# ============================================================================
# File Management
# ============================================================================

# Create temporary directory for test files
# Automatically sets TEST_TMP environment variable
create_test_tmp() {
    mkdir -p "$TEST_TMP"
}

# Clean up temporary directory (called on test file teardown)
cleanup_test_tmp() {
    if [ -d "$TEST_TMP" ]; then
        rm -rf "$TEST_TMP"
    fi
}

# ============================================================================
# Nudge Count Helpers
# ============================================================================

# Get current nudge count for a task
# Usage: COUNT=$(get_nudge_count "123")
get_nudge_count() {
    local task_id="$1"
    cat "${TEST_TMP}/task-${task_id}-nudge-count.txt" 2>/dev/null || echo "0"
}

# Set nudge count for a task
# Usage: set_nudge_count "123" "2"
set_nudge_count() {
    local task_id="$1"
    local count="$2"
    echo "$count" > "${TEST_TMP}/task-${task_id}-nudge-count.txt"
}

# ============================================================================
# Alerts Log Helpers
# ============================================================================

# Get all alerts logged to alerts file
# Usage: ALERTS=$(get_alerts)
get_alerts() {
    cat "${TEST_TMP}/task-alerts.log" 2>/dev/null || echo ""
}

# Clear alerts log
# Usage: clear_alerts
clear_alerts() {
    rm -f "${TEST_TMP}/task-alerts.log"
}

# ============================================================================
# Session State Verification
# ============================================================================

# Check if a tmux session exists
# Usage: if session_exists "$SESSION_NAME"; then ...
session_exists() {
    local session_name="$1"
    tmux has-session -t "$session_name" 2>/dev/null
}

# Get pane output from tmux session
# Usage: OUTPUT=$(get_pane_output "$SESSION_NAME")
get_pane_output() {
    local session_name="$1"
    tmux capture-pane -t "$session_name" -p
}

# Wait for a session to reach prompt (contains ">")
# Usage: wait_for_prompt "$SESSION_NAME" 30
# Returns: 0 if prompt reached, 1 if timeout
wait_for_prompt() {
    local session_name="$1"
    local timeout="${2:-30}"  # default 30 seconds
    local elapsed=0

    while [ $elapsed -lt "$timeout" ]; do
        if get_pane_output "$session_name" | grep -q ">"; then
            return 0
        fi
        sleep 1
        ((elapsed++))
    done

    return 1
}

# ============================================================================
# Bash Strict Mode
# ============================================================================

set -euo pipefail
