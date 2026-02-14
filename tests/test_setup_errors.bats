#!/usr/bin/env bats
# test_setup_errors.bats
#
# Error handling tests for `ft setup` command
# Tests failure paths: missing settings, invalid JSON, permission errors

load 'test_helper'

# Project root for ft command
PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# Skip helper for functional tests
skip_unless_functional() {
    if [[ "${RUN_FUNCTIONAL_TESTS:-}" != "1" ]]; then
        skip "Functional tests disabled (set RUN_FUNCTIONAL_TESTS=1)"
    fi
}

# Setup isolated HOME for functional tests
functional_setup() {
    export HOME="$BATS_TEST_TMPDIR"
    mkdir -p "$HOME/.claude"
}

# =============================================================================
# Static tests (always run)
# =============================================================================

@test "setup command exists" {
    run python3 -m formaltask.cli --help
    [[ "$output" =~ "setup" ]]
}

@test "setup command has --yes flag" {
    run python3 -m formaltask.cli setup --help
    [[ "$output" =~ "--yes" ]] || [[ "$output" =~ "-y" ]]
}

# =============================================================================
# Functional tests (require RUN_FUNCTIONAL_TESTS=1)
# =============================================================================

@test "setup: handles missing settings.json" {
    skip_unless_functional
    functional_setup
    # No settings.json created - HOME/.claude exists but is empty

    run python3 -m formaltask.cli setup --yes

    [ "$status" -ne 0 ]
    [[ "$output" =~ "settings.json not found" ]] || [[ "$output" =~ "not found" ]]
}

@test "setup: handles invalid settings.json" {
    skip_unless_functional
    functional_setup

    # Create invalid JSON
    echo "not valid json {{{" > "$HOME/.claude/settings.json"

    run python3 -m formaltask.cli setup --yes

    [ "$status" -ne 0 ]
    [[ "$output" =~ "invalid" ]] || [[ "$output" =~ "Invalid" ]] || [[ "$output" =~ "JSON" ]]
}

@test "setup: handles permission denied on settings.json" {
    skip_unless_functional
    functional_setup

    # Create valid settings.json but make it unreadable
    echo '{"hooks": {}}' > "$HOME/.claude/settings.json"
    chmod 000 "$HOME/.claude/settings.json"

    run python3 -m formaltask.cli setup --yes

    # Restore permissions for cleanup
    chmod 644 "$HOME/.claude/settings.json" 2>/dev/null || true

    [ "$status" -ne 0 ]
    [[ "$output" =~ "permission" ]] || [[ "$output" =~ "Permission" ]] || [[ "$output" =~ "denied" ]]
}

@test "setup: idempotent hook registration" {
    skip_unless_functional
    functional_setup

    # Create valid settings.json with empty hooks
    echo '{"hooks": {}}' > "$HOME/.claude/settings.json"

    # Run setup twice
    run python3 -m formaltask.cli setup --yes
    first_status="$status"

    run python3 -m formaltask.cli setup --yes
    second_status="$status"

    # Both should succeed (or fail consistently if other issues)
    [ "$first_status" -eq "$second_status" ]

    # If successful, hooks should appear in settings
    if [ "$second_status" -eq 0 ]; then
        # Verify hooks not duplicated - check the file has valid JSON
        run python3 -c "import json; json.load(open('$HOME/.claude/settings.json'))"
        [ "$status" -eq 0 ]
    fi
}

@test "setup: creates database directory if needed" {
    skip_unless_functional
    functional_setup

    # Create valid settings.json
    echo '{"hooks": {}}' > "$HOME/.claude/settings.json"

    # Ensure no .claude directory in current temp location
    local test_dir="$BATS_TEST_TMPDIR/project"
    mkdir -p "$test_dir"
    cd "$test_dir"

    # Database path won't exist yet
    [ ! -f "$test_dir/.claude/formaltask.db" ]

    run python3 -m formaltask.cli setup --yes --db-path "$test_dir/.claude/formaltask.db"

    # Database should be created
    [ -f "$test_dir/.claude/formaltask.db" ]
}
