#!/usr/bin/env bats
# Tests for pre-compact/capture-agent-context.sh

setup() {
    export TEST_DIR="$(mktemp -d)"
    export MEMORY_KEEPER_DB="$TEST_DIR/memory-keeper.db"
    export CLAUDE_HOOKS_LOG_DIR="$TEST_DIR/logs"
    export HOME="$TEST_DIR"

    mkdir -p "$CLAUDE_HOOKS_LOG_DIR"
    mkdir -p "$TEST_DIR/.claude/tmp"

    # Create mock memory-keeper database (empty - no sessions)
    sqlite3 "$MEMORY_KEEPER_DB" <<SQL
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE context_items (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT NOT NULL,
    created_at TEXT NOT NULL
);
SQL
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "hook exits 0 when no active session" {
    # Empty database - no sessions
    # Use PROJECT_ROOT set in setup (or resolve dynamically)
    PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && git rev-parse --show-toplevel)}"

    run "$PROJECT_ROOT/hooks/pre-compact/capture-agent-context.sh"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "No active memory-keeper session" ]]
}
