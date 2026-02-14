#!/usr/bin/env bats
# Tests for task-start script

SCRIPT="$HOME/.claude/bin/task-start"

setup() {
    TEST_DIR=$(mktemp -d)

    # Create mock main repo with git
    MAIN_REPO="$TEST_DIR/main-repo"
    mkdir -p "$MAIN_REPO/.claude"
    cd "$MAIN_REPO"
    git init -q
    git commit --allow-empty -m "Initial commit" -q

    # Create mock FormalTask database
    DB_PATH="$MAIN_REPO/.claude/formaltask.db"
    sqlite3 "$DB_PATH" "
        CREATE TABLE epics (name TEXT PRIMARY KEY, status TEXT);
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            title TEXT,
            status TEXT,
            started_at TEXT,
            epic_name TEXT
        );
        CREATE TABLE work_sessions (
            worktree_path TEXT PRIMARY KEY,
            current_task_id INTEGER
        );
        INSERT INTO epics VALUES ('test-epic', 'active');
        INSERT INTO tasks (id, title, status, epic_name) VALUES (999, 'Test Task Title', 'open', 'test-epic');
    "

    export PROJECT_ROOT="$MAIN_REPO"
}

teardown() {
    cd /
    # Clean up worktrees first
    if [ -d "$MAIN_REPO" ]; then
        cd "$MAIN_REPO"
        git worktree list --porcelain | grep "^worktree" | grep -v "$MAIN_REPO$" | cut -d' ' -f2 | while read wt; do
            git worktree remove "$wt" --force 2>/dev/null || true
        done
    fi
    rm -rf "$TEST_DIR"
}

@test "task-start requires task_id argument" {
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "task-start creates worktree with task binding" {
    cd "$MAIN_REPO"
    run "$SCRIPT" 999
    [ "$status" -eq 0 ]

    # Verify worktree exists
    [ -d "$MAIN_REPO/../task-999-test-task-title" ]

    # Verify .task/ binding
    [ -f "$MAIN_REPO/../task-999-test-task-title/.task/id" ]
    [ "$(cat "$MAIN_REPO/../task-999-test-task-title/.task/id")" = "999" ]
}

@test "task-start updates database" {
    cd "$MAIN_REPO"
    run "$SCRIPT" 999
    [ "$status" -eq 0 ]

    # Verify work_sessions entry
    session=$(sqlite3 "$DB_PATH" "SELECT current_task_id FROM work_sessions WHERE current_task_id = 999")
    [ "$session" = "999" ]

    # Verify task status updated
    status=$(sqlite3 "$DB_PATH" "SELECT status FROM tasks WHERE id = 999")
    [ "$status" = "in_progress" ]
}

@test "task-start writes epic name to .task/epic file" {
    cd "$MAIN_REPO"
    run "$SCRIPT" 999
    [ "$status" -eq 0 ]

    # Verify .task/epic file exists and contains epic name
    [ -f "$MAIN_REPO/../task-999-test-task-title/.task/epic" ]
    [ "$(cat "$MAIN_REPO/../task-999-test-task-title/.task/epic")" = "test-epic" ]
}

@test "task-start writes worktree path to .task/project_root not main repo" {
    cd "$MAIN_REPO"
    run "$SCRIPT" 999
    [ "$status" -eq 0 ]

    worktree_path="$MAIN_REPO/../task-999-test-task-title"
    # Use pwd -P to resolve symlinks (macOS /var -> /private/var)
    worktree_abs=$(cd "$worktree_path" && pwd -P)

    # project_root should be the worktree, not the main repo
    # This ensures Claude edits files in the worktree, not the main repo
    [ -f "$worktree_path/.task/project_root" ]
    project_root_value=$(cat "$worktree_path/.task/project_root")
    [ "$project_root_value" = "$worktree_abs" ]
}
