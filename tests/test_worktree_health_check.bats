#!/usr/bin/env bats
# Tests for worktree-health-check script
# Task #1324: Clean up existing detached HEAD worktrees

# Use source script directly for TDD - symlink created separately
BATS_TEST_DIRNAME="${BATS_TEST_DIRNAME:-$(dirname "$BATS_TEST_FILENAME")}"
SCRIPT="$BATS_TEST_DIRNAME/../scripts/bin/worktree-health-check"

setup() {
    TEST_DIR=$(mktemp -d)

    # Create mock main repo with git
    MAIN_REPO="$TEST_DIR/main-repo"
    mkdir -p "$MAIN_REPO"
    cd "$MAIN_REPO"
    git init -q
    git commit --allow-empty -m "Initial commit" -q

    export PROJECT_ROOT="$MAIN_REPO"
}

teardown() {
    cd /
    if [ -d "$MAIN_REPO" ]; then
        cd "$MAIN_REPO"
        git worktree list --porcelain | grep "^worktree" | grep -v "$MAIN_REPO$" | cut -d' ' -f2 | while read wt; do
            git worktree remove "$wt" --force 2>/dev/null || true
        done
    fi
    rm -rf "$TEST_DIR"
}

@test "worktree-health-check script has main function" {
    # TDD-recognized grep pattern for bash function existence
    grep -q 'main()' "$SCRIPT"
}

@test "detects detached HEAD worktrees" {
    cd "$MAIN_REPO"

    # Create a worktree in detached HEAD state
    commit_sha=$(git rev-parse HEAD)
    git worktree add --detach "$TEST_DIR/detached-worktree" "$commit_sha" -q

    # Verify it's actually detached
    git worktree list | grep -q "(detached HEAD)"

    # Run the script and check output
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Found 1 detached HEAD worktree"* ]]
}

@test "creates branch for detached HEAD worktree" {
    cd "$MAIN_REPO"

    # Create a worktree in detached HEAD state with task-like name
    commit_sha=$(git rev-parse HEAD)
    git worktree add --detach "$TEST_DIR/task-123-test-task" "$commit_sha" -q

    # Run the script
    run "$SCRIPT"
    [ "$status" -eq 0 ]

    # Verify branch was created (name derived from worktree directory)
    git branch --list | grep -q "task-123-test-task"

    # Verify output shows branch creation
    [[ "$output" == *"Created branch task-123-test-task"* ]]
}

@test "idempotent - safe to run multiple times" {
    cd "$MAIN_REPO"

    # Create a worktree in detached HEAD state
    commit_sha=$(git rev-parse HEAD)
    git worktree add --detach "$TEST_DIR/task-456-idempotent" "$commit_sha" -q

    # Run the script twice
    run "$SCRIPT"
    [ "$status" -eq 0 ]

    # Second run should also succeed (no detached HEAD remaining)
    run "$SCRIPT"
    [ "$status" -eq 0 ]

    # Should report no detached worktrees on second run
    [[ "$output" != *"Found"*"detached HEAD"* ]]
}

@test "reports nothing when no detached HEAD worktrees exist" {
    cd "$MAIN_REPO"

    # Create a normal worktree (not detached)
    git worktree add "$TEST_DIR/normal-worktree" -b normal-branch -q

    # Run the script
    run "$SCRIPT"
    [ "$status" -eq 0 ]

    # Should output "Done." with no "Found" or "Summary" messages (pattern match is more robust)
    [[ "$output" == *"Done."* ]]
    [[ "$output" != *"Found"* ]]
    [[ "$output" != *"Summary"* ]]
}

@test "P1: handles pre-existing branch name conflict gracefully" {
    cd "$MAIN_REPO"

    # Create a branch with the same name as the worktree we'll create
    git branch task-conflict-test

    # Create a detached worktree with same name as existing branch
    commit_sha=$(git rev-parse HEAD)
    git worktree add --detach "$TEST_DIR/task-conflict-test" "$commit_sha" -q

    # Run the script - should NOT fail, should report the conflict
    run "$SCRIPT"
    [ "$status" -eq 0 ]

    # Should indicate the branch already exists or was skipped
    [[ "$output" == *"already exists"* ]] || [[ "$output" == *"Skipped"* ]]
}

@test "P2: worktree is no longer detached after fix" {
    cd "$MAIN_REPO"

    # Create a detached worktree
    commit_sha=$(git rev-parse HEAD)
    git worktree add --detach "$TEST_DIR/task-789-verify-state" "$commit_sha" -q

    # Verify it's detached before fix
    git worktree list | grep "task-789-verify-state" | grep -q "(detached HEAD)"

    # Run the script
    run "$SCRIPT"
    [ "$status" -eq 0 ]

    # Verify worktree is NO LONGER detached
    ! git worktree list | grep "task-789-verify-state" | grep -q "(detached HEAD)"

    # Verify it now shows the branch name
    git worktree list | grep "task-789-verify-state" | grep -q "\[task-789-verify-state\]"
}

@test "P2: handles multiple detached worktrees with summary" {
    cd "$MAIN_REPO"

    commit_sha=$(git rev-parse HEAD)

    # Create 3 detached worktrees
    git worktree add --detach "$TEST_DIR/task-multi-1" "$commit_sha" -q
    git worktree add --detach "$TEST_DIR/task-multi-2" "$commit_sha" -q
    git worktree add --detach "$TEST_DIR/task-multi-3" "$commit_sha" -q

    # Run the script
    run "$SCRIPT"
    [ "$status" -eq 0 ]

    # Should find all 3
    [[ "$output" == *"Found 3 detached HEAD worktree"* ]]

    # Should show summary with counts
    [[ "$output" == *"Summary:"* ]]
    [[ "$output" == *"3 created"* ]]

    # All 3 branches should exist
    git branch --list | grep -q "task-multi-1"
    git branch --list | grep -q "task-multi-2"
    git branch --list | grep -q "task-multi-3"
}
