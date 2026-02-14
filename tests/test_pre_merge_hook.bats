#!/usr/bin/env bats
# Tests for pre-merge-commit hook
# This hook blocks merges when task is not completed

setup() {
    TEST_DIR=$(mktemp -d)

    # Save the real project root for Python imports
    REAL_PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"

    # Create mock main repo with git
    MAIN_REPO="$TEST_DIR/main-repo"
    mkdir -p "$MAIN_REPO/.claude"
    cd "$MAIN_REPO"
    git init -q
    git commit --allow-empty -m "Initial commit" -q

    # Create mock test database with test data
    DB_PATH="$MAIN_REPO/.claude/test_tasks.db"
    sqlite3 "$DB_PATH" "CREATE TABLE tasks (id INTEGER PRIMARY KEY, status TEXT NOT NULL DEFAULT 'open');"
    sqlite3 "$DB_PATH" "INSERT INTO tasks (id, status) VALUES (100, 'completed');"
    sqlite3 "$DB_PATH" "INSERT INTO tasks (id, status) VALUES (200, 'in_progress');"
    sqlite3 "$DB_PATH" "INSERT INTO tasks (id, status) VALUES (300, 'open');"
    sqlite3 "$DB_PATH" "INSERT INTO tasks (id, status) VALUES (400, 'pending_merge');"

    export PROJECT_ROOT="$MAIN_REPO"

    # Create the pre-merge-commit hook directory
    HOOK_PATH="$MAIN_REPO/.git/hooks/pre-merge-commit"
    mkdir -p "$MAIN_REPO/.git/hooks"
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

# Helper to create and checkout a branch
create_branch() {
    local branch_name="$1"
    cd "$MAIN_REPO"
    git checkout -b "$branch_name" -q 2>/dev/null || git checkout "$branch_name" -q
}

@test "pre-merge-commit allows merge for completed task" {
    create_branch "task-100-feature"

    run python3 -c "
import sys
sys.path.insert(0, '$REAL_PROJECT_ROOT')
from formaltask.tasks.status import check_merge_allowed
result = check_merge_allowed('task-100-feature', '$DB_PATH')
sys.exit(0 if result['allowed'] else 1)
"
    [ "$status" -eq 0 ]
}

@test "pre-merge-commit blocks merge for in_progress task" {
    create_branch "task-200-wip"

    run python3 -c "
import sys
sys.path.insert(0, '$REAL_PROJECT_ROOT')
from formaltask.tasks.status import check_merge_allowed
result = check_merge_allowed('task-200-wip', '$DB_PATH')
sys.exit(0 if result['allowed'] else 1)
"
    [ "$status" -eq 1 ]
}

@test "pre-merge-commit allows merge for non-task branch" {
    create_branch "feature/new-feature"

    run python3 -c "
import sys
sys.path.insert(0, '$REAL_PROJECT_ROOT')
from formaltask.tasks.status import check_merge_allowed
result = check_merge_allowed('feature/new-feature', '$DB_PATH')
sys.exit(0 if result['allowed'] else 1)
"
    [ "$status" -eq 0 ]
}

@test "pre-merge-commit allows merge when task not in database" {
    create_branch "task-999-deleted"

    run python3 -c "
import sys
sys.path.insert(0, '$REAL_PROJECT_ROOT')
from formaltask.tasks.status import check_merge_allowed
result = check_merge_allowed('task-999-deleted', '$DB_PATH')
sys.exit(0 if result['allowed'] else 1)
"
    [ "$status" -eq 0 ]
}

@test "pre-merge-commit handles task ID with slash separator" {
    create_branch "task/100/feature"

    run python3 -c "
import sys
sys.path.insert(0, '$REAL_PROJECT_ROOT')
from formaltask.tasks.status import check_merge_allowed
result = check_merge_allowed('task/100/feature', '$DB_PATH')
sys.exit(0 if result['allowed'] else 1)
"
    [ "$status" -eq 0 ]
}

@test "pre-merge-commit hook script exists in main repo" {
    # Get the main repo's git hooks directory
    # For worktrees, we need to find the main repo
    MAIN_REPO_GIT=$(cd "$REAL_PROJECT_ROOT" && git rev-parse --git-common-dir 2>/dev/null)
    HOOK_SCRIPT="$MAIN_REPO_GIT/hooks/pre-merge-commit"

    # Check hook exists and is executable
    [ -x "$HOOK_SCRIPT" ]
}
