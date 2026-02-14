#!/usr/bin/env bats
# Tests for get-current-epic.sh - Epic context detector

setup() {
    # Create temporary test directory
    TEST_DIR="$(mktemp -d)"
    cd "$TEST_DIR"

    # Initialize git repo
    git init -q
    git config user.email "test@example.com"
    git config user.name "Test User"

    # Create initial commit
    touch README.md
    git add README.md
    git commit -q -m "Initial commit"

    # Path to script under test
    SCRIPT="${BATS_TEST_DIRNAME}/../get-current-epic.sh"
}

teardown() {
    # Clean up test directory
    cd /
    rm -rf "$TEST_DIR"
}

@test "returns epic name when on epic/* branch" {
    git checkout -q -b epic/authentication

    run bash "$SCRIPT"

    [ "$status" -eq 0 ]
    [ "$output" = "authentication" ]
}

@test "returns content from .epic-context file when not on epic branch" {
    # Create .epic-context file
    echo "my-epic-name" > .epic-context

    run bash "$SCRIPT"

    [ "$status" -eq 0 ]
    [ "$output" = "my-epic-name" ]
}
