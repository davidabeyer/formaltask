#!/usr/bin/env bats

# Tests for commit enforcement in PM workflow

setup() {
    SCRIPT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

    # Create temp git repository
    export TEST_REPO=$(mktemp -d)
    cd "$TEST_REPO"
    
    git init
    git config user.email "test@example.com"
    git config user.name "Test User"
    
    # Create initial commit
    echo "initial" > README.md
    git add README.md
    git commit -m "Initial commit"
}

teardown() {
    rm -rf "$TEST_REPO"
}

# Test: check-git-clean.sh detects uncommitted changes
@test "detects uncommitted changes" {
    # Create uncommitted changes
    echo "modified" > README.md
    
    run bash "$SCRIPT_DIR/check-git-clean.sh"
    
    [ "$status" -eq 1 ]
    [[ "$output" =~ "uncommitted changes" ]]
}

# Test: check-git-clean.sh passes when clean
@test "passes when working directory is clean" {
    run bash "$SCRIPT_DIR/check-git-clean.sh"
    
    [ "$status" -eq 0 ]
}

# Test: check-git-clean.sh detects untracked files
@test "detects untracked files" {
    echo "new file" > untracked.txt
    
    run bash "$SCRIPT_DIR/check-git-clean.sh"
    
    [ "$status" -eq 1 ]
    [[ "$output" =~ "uncommitted changes" ]]
}

# Test: generate-commit-message.sh creates proper format
@test "generates commit message from issue number and title" {
    run bash "$SCRIPT_DIR/generate-commit-message.sh" 123 "Fix authentication bug"
    
    [ "$status" -eq 0 ]
    [[ "$output" =~ "fix: Fix authentication bug" ]]
    [[ "$output" =~ "Resolves #123" ]]
}

# Test: generate-commit-message.sh includes agent summary
@test "includes agent work summary in commit message" {
    # Create temp epic directory with agent report
    mkdir -p .claude/epics/test-epic/updates/123
    cat > .claude/epics/test-epic/updates/123/stream-a.md << 'REPORT'
## Summary
Implemented user authentication with JWT tokens
REPORT
    
    run bash "$SCRIPT_DIR/generate-commit-message.sh" 123 "Add JWT authentication" ".claude/epics/test-epic"
    
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Implemented user authentication with JWT tokens" ]]
}
