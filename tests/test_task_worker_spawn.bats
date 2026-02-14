#!/usr/bin/env bats
# Tests for task-worker-spawn script

SCRIPT="$HOME/.claude/bin/task-worker-spawn"

# Helper: Wait for tmux session to have a valid pane PID
wait_for_pane_ready() {
    local session_name="$1"
    local timeout="${2:-50}"
    local count=0
    while [ $count -lt $timeout ]; do
        if tmux list-panes -t "$session_name" -F '#{pane_pid}' 2>/dev/null | grep -q '^[0-9]'; then
            return 0
        fi
        sleep 0.1
        count=$((count + 1))
    done
    return 1
}

# Helper: Wait for a specific process to start in a session
wait_for_process() {
    local session_name="$1"
    local process_name="$2"
    local timeout="${3:-50}"
    local count=0
    while [ $count -lt $timeout ]; do
        local pane_pid
        pane_pid=$(tmux list-panes -t "$session_name" -F '#{pane_pid}' 2>/dev/null | head -1)
        if [ -n "$pane_pid" ]; then
            local pane_comm
            pane_comm=$(ps -o comm= -p "$pane_pid" 2>/dev/null || echo "")
            if [[ "$pane_comm" == "$process_name" ]]; then
                return 0
            fi
            if pgrep -P "$pane_pid" -x "$process_name" >/dev/null 2>&1; then
                return 0
            fi
        fi
        sleep 0.1
        count=$((count + 1))
    done
    return 1
}

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
        INSERT INTO tasks (id, title, status, epic_name) VALUES (997, 'Spawn Test Task', 'open', 'test-epic');
    "

    export PROJECT_ROOT="$MAIN_REPO"
}

teardown() {
    cd /
    # Clean up ALL test tmux sessions (not just task-997)
    for sess in task-997 zombie-test-sess healthy-test-sess verify-test-sess timeout-test-sess trust-test-sess taskid-test-sess; do
        tmux kill-session -t "$sess" 2>/dev/null || true
    done

    # Clean up worktrees
    if [ -d "$MAIN_REPO" ]; then
        cd "$MAIN_REPO"
        git worktree list --porcelain | grep "^worktree" | grep -v "$MAIN_REPO$" | cut -d' ' -f2 | while read wt; do
            git worktree remove "$wt" --force 2>/dev/null || true
        done
    fi
    rm -rf "$TEST_DIR"
}

@test "task-worker-spawn requires task_id argument" {
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "task-worker-spawn rejects non-numeric task_id" {
    run "$SCRIPT" "abc"
    [ "$status" -eq 1 ]
    [[ "$output" == *"numeric"* ]]
}

@test "task-worker-spawn creates tmux session with worktree" {
    cd "$MAIN_REPO"
    run "$SCRIPT" 997 "echo test"
    [ "$status" -eq 0 ]

    # Verify tmux session exists
    tmux has-session -t task-997
    [ "$?" -eq 0 ]

    # Verify output includes attach command
    [[ "$output" == *"attach"* ]] || [[ "$output" == *"task-997"* ]]
}

@test "task-worker-spawn is idempotent for healthy sessions" {
    cd "$MAIN_REPO"
    # Create session with long-running node to simulate healthy Claude
    tmux new-session -d -s "task-997" "node -e 'setInterval(() => {}, 1000)'"
    wait_for_process "task-997" "node" 30

    # Second run should detect existing healthy session
    run "$SCRIPT" 997 "echo test"
    [ "$status" -eq 0 ]
    [[ "$output" == *"already exists"* ]] || [[ "$output" == *"Already"* ]]
}

@test "task-worker-spawn creates worktree via task-start" {
    cd "$MAIN_REPO"
    run "$SCRIPT" 997 "echo test"
    [ "$status" -eq 0 ]

    # Verify worktree was created
    [ -d "$MAIN_REPO/../task-997-spawn-test-task" ]
}

@test "task-worker-spawn tmux session runs in worktree directory not main repo" {
    cd "$MAIN_REPO"
    run "$SCRIPT" 997 "echo test"
    [ "$status" -eq 0 ]

    # Get the tmux session's working directory (tmux resolves symlinks)
    session_pwd=$(tmux display-message -t task-997 -p '#{pane_current_path}')

    # Expected worktree path - use realpath to match tmux's symlink resolution
    expected_worktree="$MAIN_REPO/../task-997-spawn-test-task"
    # On macOS, /var is symlink to /private/var - need consistent resolution
    expected_worktree_resolved=$(cd "$expected_worktree" 2>/dev/null && pwd -P)

    # CRITICAL: Session must be in worktree, NOT in main repo
    # This is the bug we're fixing - sessions were running in main repo
    main_repo_resolved=$(cd "$MAIN_REPO" && pwd -P)
    [ "$session_pwd" != "$main_repo_resolved" ]

    # Compare using basename to avoid symlink resolution differences
    session_basename=$(basename "$session_pwd")
    expected_basename=$(basename "$expected_worktree_resolved")
    [ "$session_basename" = "$expected_basename" ]
}

@test "task-worker-spawn uses --permission-mode dontAsk flag" {
    # Verify the script contains --permission-mode dontAsk
    # This ensures workers run with pre-approved permissions from settings.json
    grep -q "\-\-permission-mode dontAsk" "$SCRIPT"
    [ "$?" -eq 0 ]
}

@test "task-worker-spawn default prompt uses #task:ID pattern for context injection" {
    # Task #1035: Default prompt must include #task:ID to trigger UserPromptSubmit hook
    # This replaces the old SessionStart-based context injection
    grep -q '#task:\${task_id}' "$SCRIPT" || grep -q '#task:${task_id}' "$SCRIPT"
    [ "$?" -eq 0 ]
}

# =============================================================================
# Zombie Session Detection Tests (Task #1344)
# =============================================================================

@test "is_zombie_session returns true for session with only shell" {
    # Create a tmux session with just a shell (simulates zombie)
    tmux new-session -d -s "zombie-test-sess" "bash"
    wait_for_pane_ready "zombie-test-sess" 30

    # Source script to get function
    source "$SCRIPT"

    # Session with shell only should be detected as zombie (return 0)
    run is_zombie_session "zombie-test-sess"
    tmux kill-session -t "zombie-test-sess" 2>/dev/null || true
    [ "$status" -eq 0 ]
}

@test "is_zombie_session returns false for session with node process" {
    # Create a tmux session with a node process (simulates healthy Claude)
    tmux new-session -d -s "healthy-test-sess" "node -e 'setTimeout(() => {}, 60000)'"
    wait_for_process "healthy-test-sess" "node" 50

    # Source script to get function
    source "$SCRIPT"

    # Session with node should NOT be detected as zombie (return 1)
    run is_zombie_session "healthy-test-sess"
    tmux kill-session -t "healthy-test-sess" 2>/dev/null || true
    [ "$status" -eq 1 ]
}

@test "is_zombie_session returns true for session with empty pane_pid" {
    # Verify the code handles empty pane_pid by returning zombie (0)
    # Check that script returns 0 (zombie) when pane_pid is empty
    grep -A1 'if \[ -z "\$pane_pid" \]' "$SCRIPT" | grep -q 'return 0'
}

@test "verify_claude_started returns success when node starts" {
    # Create a session that starts node
    tmux new-session -d -s "verify-test-sess" "node -e 'setInterval(() => {}, 1000)'"

    # Source script to get function
    source "$SCRIPT"

    # Should succeed as node is running
    # Cleanup before assertion (BATS anti-pattern fix)
    run verify_claude_started "verify-test-sess" 500
    tmux kill-session -t "verify-test-sess" 2>/dev/null || true
    [ "$status" -eq 0 ]
}

@test "verify_claude_started returns failure on timeout" {
    # Create a session with just a shell (no node)
    tmux new-session -d -s "timeout-test-sess" "bash"

    # Source script to get function
    source "$SCRIPT"

    # Should fail after timeout as no node starts
    # Cleanup before assertion (BATS anti-pattern fix)
    run verify_claude_started "timeout-test-sess" 200
    tmux kill-session -t "timeout-test-sess" 2>/dev/null || true
    [ "$status" -eq 1 ]
}

@test "task-worker-spawn calls verify_claude_started after spawning" {
    # Task #1344 requirement: Verify 'node' is running before returning success
    # Script must call verify_claude_started to confirm Claude actually started
    grep -q 'verify_claude_started.*session_name' "$SCRIPT"
}

@test "verify_claude_started detects trust prompt and sends Enter" {
    # verify_claude_started should check pane content for trust prompt
    # and send Enter key to accept it
    grep -q 'capture-pane' "$SCRIPT"
    grep -q 'trust' "$SCRIPT"
    grep -q 'send-keys' "$SCRIPT"
}

@test "task-worker-spawn kills zombie session and respawns" {
    cd "$MAIN_REPO"

    # Create a zombie session (just a shell, no Claude/node)
    tmux new-session -d -s "task-997" "bash"
    wait_for_pane_ready "task-997" 30

    # Verify it's a zombie
    source "$SCRIPT"
    run is_zombie_session "task-997"
    [ "$status" -eq 0 ]  # Is a zombie

    # Run spawn - should detect zombie, kill it, and create new session
    run "$SCRIPT" 997 "echo test"
    [ "$status" -eq 0 ]
    spawn_output="$output"

    # Verify session exists
    run tmux has-session -t task-997
    [ "$status" -eq 0 ]

    # Verify output mentions zombie recovery
    [[ "$spawn_output" == *"Killed zombie session: task-997"* ]]
}

# =============================================================================
# TASK_ID Environment Propagation Tests (Task #1466)
# =============================================================================

@test "tmux -e flag passes TASK_ID to session environment" {
    # This is an integration test for the TASK_ID propagation fix
    # The fix uses tmux new-session -e TASK_ID=X to pass env vars to detached sessions

    # Check tmux version supports -e flag (3.2+)
    tmux_version=$(tmux -V 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
    tmux_major=$(echo "$tmux_version" | cut -d. -f1)
    tmux_minor=$(echo "$tmux_version" | cut -d. -f2)

    if ! [[ -n "$tmux_version" ]] || ! [[ "$tmux_major" -ge 3 ]] || ! [[ "$tmux_minor" -ge 2 || "$tmux_major" -gt 3 ]]; then
        skip "tmux ${tmux_version:-unknown} does not support -e flag (requires 3.2+)"
    fi

    # Create a session with TASK_ID passed via -e flag
    tmux new-session -d -e TASK_ID=12345 -s "taskid-test-sess" "bash"
    wait_for_pane_ready "taskid-test-sess" 30

    # Send command to echo TASK_ID and capture output
    tmux send-keys -t "taskid-test-sess" 'echo "TASK_ID=$TASK_ID"' Enter
    sleep 0.5

    # Capture pane content
    pane_content=$(tmux capture-pane -t "taskid-test-sess" -p)

    # Cleanup before assertion (BATS anti-pattern fix)
    tmux kill-session -t "taskid-test-sess" 2>/dev/null || true

    # Verify TASK_ID was passed correctly
    [[ "$pane_content" == *"TASK_ID=12345"* ]]
}

@test "task-worker-spawn script uses tmux -e flag for TASK_ID" {
    # Verify the script passes TASK_ID via -e flag (tmux 3.2+ path)
    grep -q 'tmux new-session -d -e TASK_ID=' "$SCRIPT"
    [ "$?" -eq 0 ]
}

@test "task-worker-spawn validates task_id is numeric before passing to tmux" {
    # Security: Verify script validates task_id to prevent injection
    grep -q '\$task_id.*=~.*\[0-9\]' "$SCRIPT"
    [ "$?" -eq 0 ]
}
