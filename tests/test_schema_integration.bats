#!/usr/bin/env bats
# Integration tests for v5 schema migration

setup() {
    # Create temporary directory for test database
    TEST_DIR="$(mktemp -d)"
    TEST_DB="${TEST_DIR}/formaltask.db"
    # Task #2652: schema moved to formaltask/data/
    SCHEMA_FILE="formaltask/data/schema.sql"
}

teardown() {
    # Clean up test database
    rm -rf "${TEST_DIR}"
}

@test "database created from scratch" {
    # Run schema migration on fresh database
    sqlite3 "${TEST_DB}" < "${SCHEMA_FILE}"

    # Verify database file exists
    [ -f "${TEST_DB}" ]

    # Verify tables created
    result=$(sqlite3 "${TEST_DB}" "SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    [ "${result}" -ge 6 ]
}

@test "schema migration is idempotent" {
    # Run schema migration first time
    sqlite3 "${TEST_DB}" < "${SCHEMA_FILE}"

    # Count master-adhoc records
    count1=$(sqlite3 "${TEST_DB}" "SELECT COUNT(*) FROM epics WHERE name='master-adhoc'")

    # Run schema migration second time (should not duplicate)
    sqlite3 "${TEST_DB}" < "${SCHEMA_FILE}"

    # Count master-adhoc records again
    count2=$(sqlite3 "${TEST_DB}" "SELECT COUNT(*) FROM epics WHERE name='master-adhoc'")

    # Should still be exactly 1
    [ "${count1}" -eq 1 ]
    [ "${count2}" -eq 1 ]
}

@test "foreign key violations are caught" {
    # Create database with schema
    sqlite3 "${TEST_DB}" < "${SCHEMA_FILE}"

    # Try to insert task with non-existent epic (should fail with foreign key enabled)
    run sqlite3 "${TEST_DB}" "PRAGMA foreign_keys = ON; INSERT INTO tasks (epic_name, title, description, created_at) VALUES ('nonexistent', 'Test', 'Test', datetime('now'))"

    # Should fail due to foreign key constraint
    [ "${status}" -ne 0 ]
}
