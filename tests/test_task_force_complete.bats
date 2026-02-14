#!/usr/bin/env bats
# Tests for task-force-complete script

SCRIPT="$HOME/.claude/bin/task-force-complete"

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
            completed_at TEXT,
            epic_name TEXT
        );
        CREATE TABLE work_sessions (
            worktree_path TEXT PRIMARY KEY,
            current_task_id INTEGER
        );
        INSERT INTO epics VALUES ('test-epic', 'active');
        INSERT INTO tasks (id, title, status, started_at, epic_name) VALUES (998, 'Done Test Task', 'in_progress', datetime('now'), 'test-epic');
    "

    export PROJECT_ROOT="$MAIN_REPO"

    # Create worktree for task 998
    WORKTREE="$MAIN_REPO/../task-998-done-test-task"
    git worktree add "$WORKTREE" -b task-998-done-test-task -q
    mkdir -p "$WORKTREE/.task"
    echo "998" > "$WORKTREE/.task/id"
    echo "$MAIN_REPO" > "$WORKTREE/.task/project_root"
    sqlite3 "$DB_PATH" "INSERT INTO work_sessions VALUES ('$WORKTREE', 998)"

    # Make a commit in the worktree
    cd "$WORKTREE"
    echo "test content" > test-file.txt
    git add test-file.txt
    git commit -m "Test commit" -q
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

@test "task-force-complete requires task_id argument or .task/id file" {
    cd "$MAIN_REPO"  # No .task/id here
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage:"* ]] || [[ "$output" == *"task_id"* ]]
}

@test "task-force-complete merges branch and updates database" {
    cd "$WORKTREE"
    run "$SCRIPT" 998
    [ "$status" -eq 0 ]

    # Verify task status is completed
    status=$(sqlite3 "$DB_PATH" "SELECT status FROM tasks WHERE id = 998")
    [ "$status" = "completed" ]

    # Verify work_sessions entry removed
    session=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM work_sessions WHERE current_task_id = 998")
    [ "$session" = "0" ]
}
