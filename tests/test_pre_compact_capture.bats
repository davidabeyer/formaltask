#!/usr/bin/env bats
# Tests for pre-compact context capture hook (Issue #93)

setup() {
    HOOK_DIR="${HOME}/.claude/hooks/pre-compact"
    TMP_DIR="${HOME}/.claude/tmp"

    # Create tmp directory if it doesn't exist
    mkdir -p "$TMP_DIR"

    # Set test session ID
    export CLAUDE_SESSION_ID="test-session-123"
}

@test "pre-compact hook directory exists" {
    [ -d "$HOOK_DIR" ]
}

@test "capture-agent-context.sh exists and is executable" {
    [ -f "${HOOK_DIR}/capture-agent-context.sh" ]
    [ -x "${HOOK_DIR}/capture-agent-context.sh" ]
}

