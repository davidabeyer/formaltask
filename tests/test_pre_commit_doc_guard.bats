#!/usr/bin/env bats
# Integration tests for doc-guard check in pre-commit hook

setup() {
    # Create temporary test directory with git repo
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "test@example.com"
    git config user.name "Test User"

    # Create minimal project structure matching documented areas
    mkdir -p hooks/lib hooks/session_end hooks/session_start hooks/cli hooks/tests .claude/skills .claude/commands .claude/agents .git/hooks

    # Copy actual pre-commit hook from project (use dynamic path resolution)
    # Note: Project uses .githooks/ (tracked) via core.hooksPath, not .git/hooks/
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && git rev-parse --show-toplevel)"
    cp "$PROJECT_ROOT/.githooks/pre-commit" .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
}

teardown() {
    # Clean up temp directory
    cd /
    rm -rf "$TEST_DIR"
}

# Test 1: Hook blocks when modifying documented area without CLAUDE.md

@test "pre-commit blocks when modifying hooks/lib without CLAUDE.md" {
    # Create a file in documented area
    cat > hooks/lib/test_util.py << 'EOF'
def test_function():
    return True
EOF

    git add hooks/lib/test_util.py
    run git commit -m "Add test utility"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Documentation checkpoint" ]]
    [[ "$output" =~ "hooks/lib/test_util.py" ]]
}

# Test 2: Hook passes when modifying documented area WITH README.md
# Note: Doc-guard checks for README.md (detailed human docs), not CLAUDE.md (agent summaries)

@test "pre-commit passes when modifying hooks/lib with README.md" {
    # Create files in documented area
    cat > hooks/lib/test_util.py << 'EOF'
def test_function():
    return True
EOF

    cat > README.md << 'EOF'
# Updated documentation
EOF

    git add hooks/lib/test_util.py README.md
    run git commit -m "Add utility with docs"

    [ "$status" -eq 0 ]
}

# Test 3: Hook passes when modifying non-documented areas

@test "pre-commit passes when modifying non-documented files" {
    # Create a file outside documented areas
    cat > README.md << 'EOF'
# Test Project
EOF

    git add README.md
    run git commit -m "Update README"

    [ "$status" -eq 0 ]
}

# Test 4: Hook blocks for session-end

@test "pre-commit blocks when modifying hooks/session_end without CLAUDE.md" {
    cat > hooks/session_end/worker.py << 'EOF'
def process():
    pass
EOF

    git add hooks/session_end/worker.py
    run git commit -m "Update session-end"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Documentation checkpoint" ]]
}

# Test 5: Hook blocks for skills

@test "pre-commit blocks when modifying .claude/skills without CLAUDE.md" {
    mkdir -p .claude/skills/test-skill
    cat > .claude/skills/test-skill/skill.md << 'EOF'
# Test Skill
EOF

    git add .claude/skills/test-skill/skill.md
    run git commit -m "Add test skill"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Documentation checkpoint" ]]
}

# Test 6: Hook blocks for commands

@test "pre-commit blocks when modifying .claude/commands without CLAUDE.md" {
    cat > .claude/commands/test.md << 'EOF'
# Test Command
EOF

    git add .claude/commands/test.md
    run git commit -m "Add test command"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Documentation checkpoint" ]]
}

# Test 7: Hook allows bypass with --no-verify

@test "pre-commit can be bypassed with --no-verify" {
    cat > hooks/lib/test_util.py << 'EOF'
def test_function():
    return True
EOF

    git add hooks/lib/test_util.py
    run git commit --no-verify -m "Skip doc guard"

    [ "$status" -eq 0 ]
}

# Test 8: SKIP_DOC_GUARD env var bypasses doc-guard check

@test "pre-commit passes with SKIP_DOC_GUARD=1 despite documented area changes" {
    # Create a file in documented area (would normally trigger doc-guard)
    cat > hooks/lib/test_util.py << 'EOF'
def test_function():
    return True
EOF

    git add hooks/lib/test_util.py

    # Should pass with SKIP_DOC_GUARD=1
    run env SKIP_DOC_GUARD=1 git commit -m "Skip doc guard via env"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "Doc-guard skipped" ]]
}

# Test 9: SKIP_DOC_GUARD=0 does NOT bypass doc-guard (negative test)

@test "pre-commit blocks when SKIP_DOC_GUARD=0 with documented area changes" {
    # Create a file in documented area (would normally trigger doc-guard)
    cat > hooks/lib/test_util.py << 'EOF'
def test_function():
    return True
EOF

    git add hooks/lib/test_util.py

    # Should NOT pass with SKIP_DOC_GUARD=0 - only "1" bypasses
    run env SKIP_DOC_GUARD=0 git commit -m "Should still block"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Documentation checkpoint" ]]
}

# Test 10: Small modifications (< 20 lines) should pass silently
# Uses same heuristics as docs_reminder.py (MODIFICATION_THRESHOLD=20)

@test "pre-commit passes for small modifications under threshold" {
    # First create and commit initial file
    cat > hooks/lib/small_change.py << 'EOF'
def existing_function():
    return True
EOF
    git add hooks/lib/small_change.py
    git commit --no-verify -m "Initial file"

    # Now make a small modification (< 20 lines)
    cat > hooks/lib/small_change.py << 'EOF'
def existing_function():
    return True

def small_addition():
    return False
EOF
    git add hooks/lib/small_change.py
    run git commit -m "Small change"

    # Should pass without prompting (only 4 lines added)
    [ "$status" -eq 0 ]
}

# Test 11: Deleted files in documented areas should trigger doc-guard

@test "pre-commit blocks when deleting file in hooks/lib without CLAUDE.md" {
    # First create and commit a file
    cat > hooks/lib/to_delete.py << 'EOF'
def will_be_deleted():
    return True
EOF
    git add hooks/lib/to_delete.py
    git commit --no-verify -m "Add file to delete"

    # Now delete it
    git rm hooks/lib/to_delete.py
    run git commit -m "Delete file"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Documentation checkpoint" ]]
}

# Test 12: Test files should NOT trigger doc-guard (hooks/tests/ not monitored)

@test "pre-commit passes when modifying test files" {
    mkdir -p hooks/tests
    cat > hooks/tests/test_something.py << 'EOF'
def test_example():
    assert True
EOF
    git add hooks/tests/test_something.py
    run git commit -m "Add test file"

    # Test files should pass - hooks/tests/ is not a documented area
    [ "$status" -eq 0 ]
}

# Test 13: Hook blocks for hooks/cli (align with docs_reminder.py)

@test "pre-commit blocks when modifying hooks/cli without CLAUDE.md" {
    mkdir -p hooks/cli
    cat > hooks/cli/new_command.py << 'EOF'
def execute():
    pass
EOF
    git add hooks/cli/new_command.py
    run git commit -m "Add CLI command"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Documentation checkpoint" ]]
}

# Test 14: Backup files should NOT trigger doc-guard (not source code)

@test "pre-commit passes when deleting backup file in documented area" {
    # First create and commit a .backup file in documented area
    cat > hooks/session_end/worker.py.backup << 'EOF'
def old_process():
    return True
EOF
    git add hooks/session_end/worker.py.backup
    git commit --no-verify -m "Add backup file"

    # Now delete the backup file
    git rm hooks/session_end/worker.py.backup
    run git commit -m "Remove backup file"

    # Should pass - backup files are not source code
    [ "$status" -eq 0 ]
}

# Test 15: .bak files should NOT trigger doc-guard (not source code)

@test "pre-commit passes when deleting .bak file in documented area" {
    # First create and commit a .bak file in documented area
    cat > hooks/lib/module.py.bak << 'EOF'
def old_function():
    return True
EOF
    git add hooks/lib/module.py.bak
    git commit --no-verify -m "Add .bak file"

    # Now delete the .bak file
    git rm hooks/lib/module.py.bak
    run git commit -m "Remove .bak file"

    # Should pass - backup files are not source code
    [ "$status" -eq 0 ]
}
