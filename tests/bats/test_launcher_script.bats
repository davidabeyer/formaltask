#!/usr/bin/env bats
# Test launcher script for pm-dashboard
# Task #1776: TDD tests for pm-dashboard.sh launcher

# Get the repository root (script is relative to repo root)
setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT_PATH="$REPO_ROOT/scripts/pm-dashboard.sh"
    export TEST_SESSION="pm-dashboard-test-$$"
}

teardown() {
    # Kill test session if exists (cleanup)
    tmux kill-session -t "$TEST_SESSION" 2>/dev/null || true
    # Clean up environment variables to prevent pollution between tests
    unset TMUX PM_DASHBOARD_SESSION 2>/dev/null || true
}

# ============================================================================
# P0: Strict Mode Tests
# ============================================================================

@test "strict mode: set -euo pipefail is enabled" {
    # Script should have strict mode on first non-comment line
    head -5 "$SCRIPT_PATH" | grep -q "set -euo pipefail"
}

@test "no while loops in script" {
    # PRP explicitly forbids while loops - TUI uses suspend() internally
    # Use regex to match actual while loop keywords (not comments/strings)
    run grep -E "^\s*while\b" "$SCRIPT_PATH"
    # grep returns exit 1 if no matches found - that's what we want
    [[ "$status" -eq 1 ]]
}

@test "kill flag with no session shows not running" {
    # Ensure no session exists - use isolated test session
    tmux kill-session -t "$TEST_SESSION" 2>/dev/null || true
    export PM_DASHBOARD_SESSION="$TEST_SESSION"
    run "$SCRIPT_PATH" -k
    [[ "$output" == *"not running"* ]]
}

@test "kill flag with existing session kills it" {
    # Create a dashboard session with isolated test name
    export PM_DASHBOARD_SESSION="$TEST_SESSION"
    tmux new-session -d -s "$TEST_SESSION"
    run "$SCRIPT_PATH" -k
    [[ "$output" == *"killed"* ]]
    # Verify session is gone
    ! tmux has-session -t "$TEST_SESSION" 2>/dev/null
}

@test "invalid directory returns exit 1" {
    run "$SCRIPT_PATH" /nonexistent/path/12345
    [[ "$status" -eq 1 ]]
    [[ "$output" == *"not found"* ]] || [[ "$output" == *"does not exist"* ]]
}

@test "help flag shows usage" {
    run "$SCRIPT_PATH" --help
    [[ "$output" == *"Usage"* ]] || [[ "$output" == *"usage"* ]]
}

@test "script calls python3 -m formaltask.cli.pm dashboard" {
    grep -q "python3 -m formaltask.cli.pm dashboard" "$SCRIPT_PATH"
}

@test "script uses tmux has-session for session detection" {
    grep -q "tmux has-session" "$SCRIPT_PATH"
}

@test "script handles TMUX environment variable" {
    # Script should check if we're inside tmux
    grep -q "TMUX" "$SCRIPT_PATH"
}

@test "script validates required tools exist" {
    # Script should check for tmux and python3
    grep -q "command -v tmux" "$SCRIPT_PATH" || grep -q "which tmux" "$SCRIPT_PATH"
    grep -q "command -v python3" "$SCRIPT_PATH" || grep -q "which python3" "$SCRIPT_PATH"
}

@test "exits with error when tmux is not installed" {
    # Create a fake PATH without tmux
    local fake_path
    fake_path=$(mktemp -d)
    # Link only essential commands (bash, python3) but NOT tmux
    ln -sf "$(command -v bash)" "$fake_path/bash"
    ln -sf "$(command -v python3)" "$fake_path/python3"
    ln -sf "$(command -v grep)" "$fake_path/grep"
    ln -sf "$(command -v head)" "$fake_path/head"
    ln -sf "$(command -v cat)" "$fake_path/cat"

    # Run script with restricted PATH
    run env PATH="$fake_path" bash "$SCRIPT_PATH"

    # Cleanup
    rm -rf "$fake_path"

    # Verify error behavior
    [[ "$status" -eq 1 ]]
    [[ "$output" == *"tmux"* ]] && [[ "$output" == *"required"* ]]
}

@test "exits with error when python3 is not installed" {
    # Create a fake PATH without python3
    local fake_path
    fake_path=$(mktemp -d)
    # Link essential commands and tmux, but NOT python3
    ln -sf "$(command -v bash)" "$fake_path/bash"
    ln -sf "$(command -v tmux)" "$fake_path/tmux"
    ln -sf "$(command -v grep)" "$fake_path/grep"
    ln -sf "$(command -v head)" "$fake_path/head"
    ln -sf "$(command -v cat)" "$fake_path/cat"

    # Run script with restricted PATH
    run env PATH="$fake_path" bash "$SCRIPT_PATH"

    # Cleanup
    rm -rf "$fake_path"

    # Verify error behavior
    [[ "$status" -eq 1 ]]
    [[ "$output" == *"python3"* ]] && [[ "$output" == *"required"* ]]
}

@test "creates detached session when inside tmux" {
    # Use isolated test session
    export PM_DASHBOARD_SESSION="$TEST_SESSION"
    # Ensure no session exists
    tmux kill-session -t "$TEST_SESSION" 2>/dev/null || true

    # Create a temporary tmux server for testing
    # Simulate being inside tmux by setting TMUX variable
    export TMUX="/tmp/test-tmux-$$,12345,0"

    # Run script - it will fail on switch-client since we're not really in tmux,
    # but it should create the detached session first
    run "$SCRIPT_PATH"
    # Note: run captures all output/status; no need for || true or 2>/dev/null

    # Verify session was created (the new-session -d should succeed before switch-client fails)
    run tmux has-session -t "$TEST_SESSION"
    [[ "$status" -eq 0 ]]
}
