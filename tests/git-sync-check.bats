#!/usr/bin/env bats
# TDD tests for git-sync-check.sh SessionStart hook

setup() {
    TEST_DIR="$(mktemp -d)"
    cd "$TEST_DIR"
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test"
    echo "initial" > file.txt
    git add file.txt
    git commit -q -m "initial"
    SCRIPT="$HOME/.claude/hooks/git-sync-check.sh"
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

@test "exits 0 when .task/id exists (worktree detection)" {
    mkdir -p .task
    echo "123" > .task/id

    run "$SCRIPT"

    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "exits 0 silently on non-master branch" {
    git checkout -q -b feature-branch

    run "$SCRIPT"

    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "shows warning when local master is behind remote" {
    # Set up a "remote" repo with extra commit
    REMOTE_DIR="$(mktemp -d)"
    git clone -q "$TEST_DIR" "$REMOTE_DIR/clone"
    cd "$REMOTE_DIR/clone"
    echo "new content" > newfile.txt
    git add newfile.txt
    git commit -q -m "remote commit"

    # Go back to original and add clone as origin
    cd "$TEST_DIR"
    git remote add origin "$REMOTE_DIR/clone"
    git fetch -q origin

    run "$SCRIPT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"behind"* ]]

    rm -rf "$REMOTE_DIR"
}

@test "no warning when local master is in sync with remote" {
    # Set up a "remote" repo (no extra commits)
    REMOTE_DIR="$(mktemp -d)"
    git clone -q --bare "$TEST_DIR" "$REMOTE_DIR/origin.git"
    git remote add origin "$REMOTE_DIR/origin.git"
    git fetch -q origin

    run "$SCRIPT"

    [ "$status" -eq 0 ]
    [ -z "$output" ]

    rm -rf "$REMOTE_DIR"
}

@test "exits 0 gracefully when git fetch fails (no remote)" {
    # No remote configured, fetch will fail
    run "$SCRIPT"

    [ "$status" -eq 0 ]
    [ -z "$output" ]
}
