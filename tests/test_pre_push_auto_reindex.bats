#!/usr/bin/env bats

# Tests for pre-push hook auto-reindex functionality
# Verifies that pushing triggers claude-context reindex in background

setup() {
    SCRIPT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
}

teardown() {
    :
}

# Test: pre-push hook should contain auto-reindex logic
@test "pre-push hook contains claude-context reindex trigger" {
    HOOK_FILE="$PROJECT_ROOT/.git/hooks/pre-push"

    # Check hook exists
    [ -f "$HOOK_FILE" ]

    # Check hook contains reindex logic for claude-context
    run grep -q "claude-context" "$HOOK_FILE"
    [ "$status" -eq 0 ]
}

# Test: pre-push hook should source credentials from ~/.context/.env
@test "pre-push hook sources credentials from context env file" {
    HOOK_FILE="$PROJECT_ROOT/.git/hooks/pre-push"

    # Check hook sources the .env file to override shell env vars
    run grep -q "source.*\.context.*\.env\|\.context.*\.env" "$HOOK_FILE"
    [ "$status" -eq 0 ]
}
