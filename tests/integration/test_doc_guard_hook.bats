#!/usr/bin/env bats
# BATS integration tests for doc_guard_hook.py (Task #902)
# Tests the Python implementation against real git operations

setup() {
    # Store original directory for PYTHONPATH
    export ORIGINAL_DIR="$BATS_TEST_DIRNAME/../../.."
    export PYTHONPATH="$ORIGINAL_DIR:$PYTHONPATH"

    # Create a temp directory for test repo
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"

    # Initialize git repo
    git init --initial-branch=main
    git config user.email "test@test.com"
    git config user.name "Test User"

    # Create initial commit
    echo "Initial content" > README.md
    git add README.md
    git commit -m "Initial commit"
}

teardown() {
    cd "$ORIGINAL_DIR"
    rm -rf "$TEST_DIR"
}

@test "doc_guard_hook passes when no staged files" {
    # No changes staged
    run python -m hooks.lib.doc_guard_hook

    [[ "$status" -eq 0 ]]
}

@test "doc_guard_hook passes when CLAUDE.md is staged" {
    # Create documented area change WITH CLAUDE.md
    mkdir -p hooks/lib
    echo "# New module" > hooks/lib/new_module.py
    echo "# Documentation" > hooks/CLAUDE.md
    git add hooks/lib/new_module.py hooks/CLAUDE.md

    run python -m hooks.lib.doc_guard_hook

    [[ "$status" -eq 0 ]]
}

@test "doc_guard_hook blocks when documented area changed without CLAUDE.md" {
    # Create documented area change WITHOUT CLAUDE.md
    mkdir -p hooks/lib
    echo "# New module" > hooks/lib/new_module.py
    git add hooks/lib/new_module.py

    # Run in batch mode (no TTY)
    export PRE_COMMIT_MODE=batch
    run python -m hooks.lib.doc_guard_hook

    [[ "$status" -eq 1 ]]
}

@test "doc_guard_hook allows small changes below threshold" {
    # Create initial file and commit it
    mkdir -p hooks/lib
    echo "line1" > hooks/lib/existing.py
    git add hooks/lib/existing.py
    git commit -m "Add existing file"

    # Modify with small change (below 20 line threshold)
    echo "line2" >> hooks/lib/existing.py
    git add hooks/lib/existing.py

    # Run in batch mode
    export PRE_COMMIT_MODE=batch
    run python -m hooks.lib.doc_guard_hook

    # Should pass because change is below threshold
    [[ "$status" -eq 0 ]]
}

@test "doc_guard_hook pre-commit yaml config is valid" {
    # Verify pre-commit config has the doc-guard entry
    cd "$ORIGINAL_DIR"

    # Check for doc-guard hook entry
    grep -q "id: doc-guard" .pre-commit-config.yaml

    # Check for correct entry point
    grep -q "entry: python -m hooks.lib.doc_guard_hook" .pre-commit-config.yaml

    # Check for always_run
    grep -q "always_run: true" .pre-commit-config.yaml
}
