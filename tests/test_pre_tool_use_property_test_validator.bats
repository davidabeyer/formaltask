#!/usr/bin/env bats
# Integration tests for property test PreToolUse hook
# Tests convention-based detection and validation behavior

setup() {
    # Get absolute path to hook script before changing directories
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && git rev-parse --show-toplevel)"
    HOOK_SCRIPT="$PROJECT_ROOT/.claude/hooks/pre-tool-use-property-test-validator.sh"

    # Create temporary test directory
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"

    # Create minimal project structure
    mkdir -p tests lib
}

teardown() {
    # Clean up temp directory
    cd /
    rm -rf "$TEST_DIR"
}

# Helper: Run hook with JSON input
run_hook() {
    local tool="$1"
    local file_path="$2"

    echo "{\"tool\":\"$tool\",\"args\":{\"file_path\":\"$file_path\"}}" | \
        bash "$HOOK_SCRIPT"
}

# ============================================================================
# Test 1: Hook passes for non-Write/Edit operations
# ============================================================================

@test "hook passes for Read operation" {
    run run_hook "Read" "lib/foo.py"

    [ "$status" -eq 0 ]
    [[ "$output" == '{"reason":""}' ]]
}

# ============================================================================
# Test 2: Hook passes when no property test file exists
# ============================================================================

@test "hook passes when property test file does not exist" {
    # Create implementation file but NO property test
    touch lib/parser.py

    run run_hook "Write" "lib/parser.py"

    [ "$status" -eq 0 ]
    [[ "$output" == '{"reason":""}' ]]
}

# ============================================================================
# Test 3: Hook passes when editing test files themselves
# ============================================================================

@test "hook passes when editing property test file itself" {
    touch tests/test_parser_properties.py

    run run_hook "Edit" "tests/test_parser_properties.py"

    [ "$status" -eq 0 ]
    [[ "$output" == '{"reason":""}' ]]
}

# ============================================================================
# Test 4: Hook passes when property tests pass
# ============================================================================

@test "hook passes when property tests pass" {
    # Create implementation file
    cat > lib/adder.py << 'EOF'
def add(a, b):
    return a + b
EOF

    # Create passing property test
    cat > tests/test_adder_properties.py << 'EOF'
from hypothesis import given
import hypothesis.strategies as st
import sys
sys.path.insert(0, 'lib')
from adder import add

@given(st.integers(), st.integers())
def test_add_commutative(a, b):
    assert add(a, b) == add(b, a)
EOF

    run run_hook "Write" "lib/adder.py"

    [ "$status" -eq 0 ]
    [[ "$output" == '{"reason":""}' ]]
}

# ============================================================================
# Test 5: Hook blocks when property tests fail
# ============================================================================

@test "hook blocks when property tests fail" {
    # Create implementation file
    cat > lib/multiplier.py << 'EOF'
def multiply(a, b):
    return a + b  # BUG: should be a * b
EOF

    # Create simple failing test (no Hypothesis to avoid flakiness)
    cat > tests/test_multiplier_properties.py << 'EOF'
import sys
sys.path.insert(0, 'lib')
from multiplier import multiply

def test_multiply_basic():
    # Simple assertion that will fail
    assert multiply(2, 3) == 6, "Expected 2 * 3 = 6"
    assert multiply(4, 5) == 20, "Expected 4 * 5 = 20"
EOF

    run run_hook "Write" "lib/multiplier.py"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Property tests failing" ]]
    [[ "$output" =~ "test_multiplier_properties.py" ]]
}

# ============================================================================
# Test 6: Hook skips non-Python files
# ============================================================================

@test "hook skips markdown files" {
    run run_hook "Write" "README.md"

    [ "$status" -eq 0 ]
    [[ "$output" == '{"reason":""}' ]]
}

@test "hook skips JSON config files" {
    run run_hook "Write" "config.json"

    [ "$status" -eq 0 ]
    [[ "$output" == '{"reason":""}' ]]
}

# ============================================================================
# Test 7: Hook handles MultiEdit operation
# ============================================================================

@test "hook validates MultiEdit operations" {
    # Create implementation and passing property test
    cat > lib/subtractor.py << 'EOF'
def subtract(a, b):
    return a - b
EOF

    cat > tests/test_subtractor_properties.py << 'EOF'
from hypothesis import given
import hypothesis.strategies as st
import sys
sys.path.insert(0, 'lib')
from subtractor import subtract

@given(st.integers())
def test_subtract_self_is_zero(a):
    assert subtract(a, a) == 0
EOF

    run run_hook "MultiEdit" "lib/subtractor.py"

    [ "$status" -eq 0 ]
    [[ "$output" == '{"reason":""}' ]]
}

# ============================================================================
# Test 8: Hook can find and run pytest
# ============================================================================

@test "hook finds pytest executable" {
    # Verify pytest is available in test environment
    run which pytest
    [ "$status" -eq 0 ]

    # Verify pytest works in temp directory
    cat > tests/test_basic.py << 'EOF'
def test_passes():
    assert True
EOF

    run pytest tests/test_basic.py -q
    [ "$status" -eq 0 ]
}

# ============================================================================
# Test 9: Hook provides helpful error messages
# ============================================================================

@test "hook error message includes file path and test location" {
    # Create failing test
    cat > lib/divider.py << 'EOF'
def divide(a, b):
    return a - b  # WRONG: should be a / b
EOF

    cat > tests/test_divider_properties.py << 'EOF'
import sys
sys.path.insert(0, 'lib')
from divider import divide

def test_divide_basic():
    # Simple failing assertion
    assert divide(10, 2) == 5, "Expected 10 / 2 = 5"
EOF

    run run_hook "Write" "lib/divider.py"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "lib/divider.py" ]]
    [[ "$output" =~ "tests/test_divider_properties.py" ]]
    [[ "$output" =~ "Fix property tests before editing" ]]
}
