#!/usr/bin/env bats
# Integration tests for gitignore configuration

@test "git ignores database file" {
    # Create test database file
    touch .claude/formaltask-test.db

    # Check if git ignores it
    run git status --short .claude/formaltask-test.db

    # Should be empty (file ignored)
    [ -z "${output}" ]

    # Clean up
    rm -f .claude/formaltask-test.db
}

@test "git ignores WAL files" {
    # Create test WAL file
    touch .claude/formaltask-test.db-wal

    # Check if git ignores it
    run git status --short .claude/formaltask-test.db-wal

    # Should be empty (file ignored)
    [ -z "${output}" ]

    # Clean up
    rm -f .claude/formaltask-test.db-wal
}
