#!/usr/bin/env bats
# Tests for stub_check() function in pre-commit hook
# Reference: plans/epics/detecting-stubs/489.md

setup() {
    # Create temp directory for test repo
    TEST_DIR="$(mktemp -d)"
    cd "$TEST_DIR"
    
    # Initialize git repo
    git init --quiet
    git config user.email "test@test.com"
    git config user.name "Test User"
    
    # Create hooks/lib directory with stub_detector
    mkdir -p hooks/lib
    cp "$BATS_TEST_DIRNAME/../lib/stub_detector.py" hooks/lib/
    
    # Copy pre-commit hook
    mkdir -p .git/hooks
    cp "$BATS_TEST_DIRNAME/../../.git/hooks/pre-commit" .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

@test "stub_check detects stub function in staged file" {
    # Create a Python file with a stub
    cat > test_module.py << 'EOF'
def placeholder():
    pass
EOF
    
    git add test_module.py
    
    # Run pre-commit (should warn about stub)
    run bash -c 'echo "n" | .git/hooks/pre-commit 2>&1'
    
    # Should contain stub warning
    [[ "$output" == *"Stub functions detected"* ]] || [[ "$output" == *"stub"* ]]
}

@test "stub_check approves clean Python file" {
    # Create a Python file without stubs
    cat > clean_module.py << 'EOF'
def real_function():
    return 42
EOF
    
    git add clean_module.py
    
    # Run pre-commit (should pass)
    run .git/hooks/pre-commit
    
    # Should indicate no stubs found
    [[ "$output" == *"No stub functions found"* ]] || [ "$status" -eq 0 ]
}

@test "stub_check skips non-Python files" {
    # Create a non-Python file
    echo '{"key": "value"}' > config.json
    
    git add config.json
    
    # Run pre-commit
    run .git/hooks/pre-commit
    
    # Should indicate no Python files
    [[ "$output" == *"No Python files staged"* ]] || [ "$status" -eq 0 ]
}
