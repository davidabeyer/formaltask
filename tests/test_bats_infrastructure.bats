#!/usr/bin/env bats
# test_bats_infrastructure.bats
#
# Tests verifying BATS test infrastructure works correctly

# Load test helper
load 'test_helper'

@test "test helper is loaded" {
    # Verify the helper file loaded successfully
    [ -n "${BATS_TEST_HELPER_LOADED:-}" ]
}

@test "setup_test_environment creates temp directory" {
    setup_test_environment
    [ -d "$TEST_TEMP_DIR" ]
    teardown_test_environment
}

@test "create_test_tmux_session creates session" {
    local session_name="bats-test-$$"
    create_test_tmux_session "$session_name"
    tmux has-session -t "$session_name" 2>/dev/null
    destroy_test_tmux_session "$session_name"
}

@test "assert_file_contains helper works" {
    setup_test_environment
    echo "test content here" > "$TEST_TEMP_DIR/test.txt"
    assert_file_contains "$TEST_TEMP_DIR/test.txt" "test content"
    teardown_test_environment
}

@test "create_mock_script creates executable script" {
    setup_test_environment
    create_mock_script "$TEST_TEMP_DIR/mock.sh" 'echo "mocked output"'
    [ -x "$TEST_TEMP_DIR/mock.sh" ]
    result=$("$TEST_TEMP_DIR/mock.sh")
    [ "$result" = "mocked output" ]
    teardown_test_environment
}
