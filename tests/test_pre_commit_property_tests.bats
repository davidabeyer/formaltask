#!/usr/bin/env bats
# Integration tests for property test validation in pre-commit hook

setup() {
    # Get absolute path to project root dynamically
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && git rev-parse --show-toplevel)"

    # Create temporary test directory with git repo
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "test@example.com"
    git config user.name "Test User"

    # Create minimal project structure
    mkdir -p lib tests .git/hooks

    # Create pre-commit hook that calls property-test-validator.sh
    cat > .git/hooks/pre-commit << 'HOOK_EOF'
#!/bin/bash
# Call property test validator
bash "$PROJECT_ROOT/hooks/property-test-validator.sh"
exit $?
HOOK_EOF
    chmod +x .git/hooks/pre-commit
}

teardown() {
    # Clean up temp directory
    cd /
    rm -rf "$TEST_DIR"
}

# Test 1: Hook passes when no property tests exist

@test "pre-commit passes when implementation modified but no property test exists" {
    # Create implementation file
    cat > lib/calculator.py << 'EOF'
def add(a, b):
    return a + b
EOF

    git add lib/calculator.py
    run git commit -m "Add calculator"

    [ "$status" -eq 0 ]
}

# Test 2: Hook blocks when property tests fail

@test "pre-commit blocks when property tests fail" {
    # Create implementation with bug
    cat > lib/divider.py << 'EOF'
def divide(a, b):
    return a - b  # BUG: should be a / b
EOF

    # Create failing property test
    cat > tests/test_divider_properties.py << 'EOF'
import sys
sys.path.insert(0, 'lib')
from divider import divide

def test_divide_basic():
    assert divide(10, 2) == 5, "Expected 10 / 2 = 5"
EOF

    git add lib/divider.py tests/test_divider_properties.py
    run git commit -m "Add divider"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Property tests failing" ]] || [[ "$output" =~ "COMMIT BLOCKED" ]]
}
