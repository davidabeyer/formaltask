#!/usr/bin/env bats
# Tests for pre-commit testmon gate
# These tests verify the test_impact_check function exists in pre-commit hook

# Dynamically resolve project root to avoid hardcoded paths
PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && git rev-parse --show-toplevel)"
PRECOMMIT_HOOK="$PROJECT_ROOT/.git/hooks/pre-commit"

setup() {
    # Create temp directory for test
    TEST_DIR="$(mktemp -d)"
    cd "$TEST_DIR"

    # Initialize git repo
    git init --quiet
    git config user.email "test@example.com"
    git config user.name "Test User"

    # Create initial commit
    echo "initial" > README.md
    git add README.md
    git commit -m "initial" --quiet
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

@test "pre-commit hook contains test_impact_check function" {
    # Verify function exists in pre-commit hook
    run grep -q "test_impact_check()" "$PRECOMMIT_HOOK"
    [ "$status" -eq 0 ]
}

@test "test_impact_check allows when no Python files staged" {
    # Create .testmondata to trigger check
    touch .testmondata

    # Stage a non-Python file
    echo "text" > file.txt
    git add file.txt

    # Source the function from pre-commit hook and run it
    run bash -c "source $PRECOMMIT_HOOK; test_impact_check"
    [ "$status" -eq 0 ]
}

@test "test_impact_check allows when source and test files staged together" {
    # Create .testmondata to trigger check
    touch .testmondata

    # Create directory structure
    mkdir -p src tests

    # Stage source file
    echo "def foo(): pass" > src/module.py
    git add src/module.py

    # Stage test file
    echo "def test_foo(): pass" > tests/test_module.py
    git add tests/test_module.py

    # Source the function from pre-commit hook and run it
    run bash -c "source $PRECOMMIT_HOOK; test_impact_check"
    [ "$status" -eq 0 ]
}

@test "test_impact_check allows in CI mode even without tests" {
    # Create .testmondata to trigger check
    touch .testmondata

    # Create directory structure
    mkdir -p src

    # Stage source file without tests
    echo "def foo(): pass" > src/module.py
    git add src/module.py

    # Non-interactive mode (stdin not a tty) - should allow
    # Source the function from pre-commit hook and run it
    run bash -c "source $PRECOMMIT_HOOK; test_impact_check"
    [ "$status" -eq 0 ]
}
