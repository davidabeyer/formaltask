#!/usr/bin/env bats
# Tests for formaltask-monitor.sh background monitoring script

setup() {
    export MONITOR_SCRIPT="$HOME/.claude/bin/formaltask-monitor.sh"
    export TEST_DIR="$(mktemp -d)"
    export TEST_DB="$TEST_DIR/formaltask.db"

    # Create test database with minimal schema
    sqlite3 "$TEST_DB" "CREATE TABLE tasks (
        id INTEGER PRIMARY KEY,
        title TEXT,
        status TEXT DEFAULT 'open',
        review_status TEXT DEFAULT 'none'
    )"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "monitor script exists and is executable" {
    [ -x "$MONITOR_SCRIPT" ]
}

@test "monitor detects tasks with review_status=passed" {
    # Insert a task with passed review
    sqlite3 "$TEST_DB" "INSERT INTO tasks (id, title, status, review_status)
                        VALUES (1, 'Test Task', 'in_progress', 'passed')"

    # Run one iteration of monitor (TEST_MODE=1 for single pass)
    run env DB_PATH="$TEST_DB" TEST_MODE=1 "$MONITOR_SCRIPT"

    # Should output merge ready alert
    [[ "$output" == *"MERGE"* ]] || [[ "$output" == *"passed"* ]] || [[ "$output" == *"Test Task"* ]]
}

@test "monitor detects stuck workers (nudge count >= 3)" {
    # Create nudge count file with 3 attempts (unique ID to avoid conflicts)
    export STUCK_NUDGE_FILE="/tmp/task-bats-stuck-test-nudge-count.txt"
    echo "3" > "$STUCK_NUDGE_FILE"

    # Run one iteration
    run env DB_PATH="$TEST_DB" TEST_MODE=1 "$MONITOR_SCRIPT"

    # Cleanup before assertion (so test result isn't masked)
    rm -f "$STUCK_NUDGE_FILE"

    # Should output stuck alert - MUST BE LAST LINE
    [[ "$output" == *"STUCK"* ]] || [[ "$output" == *"bats-stuck-test"* ]]
}

@test "monitor detects pending reviews > 20 min" {
    # Insert a task with pending review from 25 minutes ago
    local old_time=$(date -v-25M +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -d "25 minutes ago" +"%Y-%m-%d %H:%M:%S")
    sqlite3 "$TEST_DB" "ALTER TABLE tasks ADD COLUMN review_requested_at TEXT"
    sqlite3 "$TEST_DB" "INSERT INTO tasks (id, title, status, review_status, review_requested_at)
                        VALUES (1, 'Pending Review Task', 'in_progress', 'pending', '$old_time')"

    # Run one iteration
    run env DB_PATH="$TEST_DB" TEST_MODE=1 "$MONITOR_SCRIPT"

    # Should output pending review alert - MUST BE LAST LINE
    [[ "$output" == *"PENDING"* ]] || [[ "$output" == *"review"* ]] || [[ "$output" == *"Pending Review Task"* ]]
}
