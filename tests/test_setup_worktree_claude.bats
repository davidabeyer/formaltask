#!/usr/bin/env bats
# Tests for setup-worktree-claude.sh

SCRIPT="$HOME/.claude/bin/setup-worktree-claude.sh"

setup() {
    # Create temporary test directory
    TEST_DIR=$(mktemp -d)

    # Create mock main repo structure
    MAIN_REPO="$TEST_DIR/main-repo"
    mkdir -p "$MAIN_REPO/.claude/agents"
    mkdir -p "$MAIN_REPO/.claude/skills"
    mkdir -p "$MAIN_REPO/.claude/hooks"
    mkdir -p "$MAIN_REPO/.claude/scripts"
    mkdir -p "$MAIN_REPO/.claude/tdd-guard"
    echo "*.pyc" > "$MAIN_REPO/.claude/tdd-guard/ignore-patterns.txt"

    # Create mock worktree
    WORKTREE="$TEST_DIR/worktree"
    mkdir -p "$WORKTREE"

    # Initialize as git repo for auto-detection to work
    cd "$MAIN_REPO" && git init -q
    cd "$WORKTREE" && git init -q
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "script requires worktree path argument" {
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "creates symlinks for shared directories" {
    run "$SCRIPT" "$WORKTREE" "$MAIN_REPO"
    [ "$status" -eq 0 ]

    # Verify symlinks exist
    [ -L "$WORKTREE/.claude/agents" ]
    [ -L "$WORKTREE/.claude/skills" ]
    [ -L "$WORKTREE/.claude/hooks" ]
    [ -L "$WORKTREE/.claude/scripts" ]
}

@test "creates local directories for isolated state" {
    run "$SCRIPT" "$WORKTREE" "$MAIN_REPO"
    [ "$status" -eq 0 ]

    # Verify local directories exist (not symlinks)
    [ -d "$WORKTREE/.claude/tdd-guard/data" ]
    [ ! -L "$WORKTREE/.claude/tdd-guard/data" ]
    [ -d "$WORKTREE/.claude/Memory" ]
    [ ! -L "$WORKTREE/.claude/Memory" ]
    [ -d "$WORKTREE/.claude/commands" ]
    [ ! -L "$WORKTREE/.claude/commands" ]
}

@test "copies tdd-guard ignore-patterns.txt" {
    run "$SCRIPT" "$WORKTREE" "$MAIN_REPO"
    [ "$status" -eq 0 ]

    # Verify config file was copied
    [ -f "$WORKTREE/.claude/tdd-guard/ignore-patterns.txt" ]
    [ ! -L "$WORKTREE/.claude/tdd-guard/ignore-patterns.txt" ]

    # Verify content matches
    diff "$MAIN_REPO/.claude/tdd-guard/ignore-patterns.txt" "$WORKTREE/.claude/tdd-guard/ignore-patterns.txt"
}

@test "script is idempotent" {
    # Run twice
    run "$SCRIPT" "$WORKTREE" "$MAIN_REPO"
    [ "$status" -eq 0 ]

    run "$SCRIPT" "$WORKTREE" "$MAIN_REPO"
    [ "$status" -eq 0 ]

    # Verify structure still intact
    [ -L "$WORKTREE/.claude/agents" ]
    [ -d "$WORKTREE/.claude/tdd-guard/data" ]
}

@test "auto-detects main_repo from git worktree" {
    # Setup: Create a proper worktree structure
    # The main repo already has .git from setup()
    # Create worktree linked to main repo
    cd "$MAIN_REPO"
    git worktree add "$TEST_DIR/real-worktree" -b test-wt 2>/dev/null || true

    # Run script without main_repo argument
    run "$SCRIPT" "$TEST_DIR/real-worktree"
    [ "$status" -eq 0 ]

    # Verify symlinks point to main repo
    [ -L "$TEST_DIR/real-worktree/.claude/agents" ]

    # Cleanup
    git worktree remove "$TEST_DIR/real-worktree" --force 2>/dev/null || true
    git branch -D test-wt 2>/dev/null || true
}
