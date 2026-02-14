#!/usr/bin/env bash
# test_helper.bash
#
# Shared BATS test infrastructure for behavioral tests
# Load with: load 'test_helper'

# Mark that helper is loaded
export BATS_TEST_HELPER_LOADED=1

# Setup test environment with temp directory
setup_test_environment() {
    export TEST_TEMP_DIR=$(mktemp -d -t bats-test-XXXXXX)
}

# Teardown test environment and cleanup
teardown_test_environment() {
    [ -d "$TEST_TEMP_DIR" ] && rm -rf "$TEST_TEMP_DIR"
}

# Create a test tmux session
create_test_tmux_session() {
    local session_name="$1"
    tmux new-session -d -s "$session_name" 2>/dev/null
}

# Destroy a test tmux session
destroy_test_tmux_session() {
    local session_name="$1"
    tmux kill-session -t "$session_name" 2>/dev/null || true
}

# Assert file contains pattern
assert_file_contains() {
    local file="$1"
    local pattern="$2"
    grep -q "$pattern" "$file"
}

# Create a mock executable script
create_mock_script() {
    local script_path="$1"
    local script_content="$2"
    cat > "$script_path" <<EOF
#!/usr/bin/env bash
$script_content
EOF
    chmod +x "$script_path"
}
