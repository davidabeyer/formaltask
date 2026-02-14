#!/usr/bin/env bats

# Task #2364: Tests for install.sh bootstrap script
# TDD: Tests written BEFORE implementation

# Get the project root (where install.sh should be)
PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
INSTALL_SCRIPT="$PROJECT_ROOT/install.sh"

@test "install.sh exists and is executable" {
    [[ -x "$INSTALL_SCRIPT" ]]
}

@test "install.sh uses set -euo pipefail for safety" {
    run grep -E '^set -euo pipefail' "$INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "install.sh checks Python version" {
    run grep -E 'python.*version|sys\.version_info' "$INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "install.sh installs pip dependencies" {
    run grep -E 'pip install -e' "$INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "install.sh configures git hooks path" {
    run grep 'git config core.hooksPath .githooks' "$INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "install.sh passes shellcheck" {
    if ! command -v shellcheck &>/dev/null; then
        skip "shellcheck not installed"
    fi
    run shellcheck "$INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "install.sh syntax is valid" {
    run bash -n "$INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "install.sh validates pyproject.toml exists" {
    run grep 'pyproject.toml' "$INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "install.sh checks for git repository" {
    run grep 'git rev-parse' "$INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

# =============================================================================
# Functional tests (require RUN_FUNCTIONAL_TESTS=1)
# =============================================================================

# Skip helper for functional tests
skip_unless_functional() {
    if [[ "${RUN_FUNCTIONAL_TESTS:-}" != "1" ]]; then
        skip "Functional tests disabled (set RUN_FUNCTIONAL_TESTS=1)"
    fi
}

@test "install.sh: fails without python3 in PATH" {
    skip_unless_functional

    # Copy script before restricting PATH
    cd "$BATS_TEST_TMPDIR"
    cp "$INSTALL_SCRIPT" .

    # Create minimal PATH without python - only basic commands
    local temp_bin="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$temp_bin"
    # Link essential commands but NOT python3
    ln -sf /bin/bash "$temp_bin/bash"
    ln -sf /bin/echo "$temp_bin/echo"
    ln -sf /usr/bin/command "$temp_bin/command" 2>/dev/null || true

    # Run with restricted PATH
    run env PATH="$temp_bin" bash install.sh

    [ "$status" -ne 0 ]
    [[ "$output" =~ "python3" ]] || [[ "$output" =~ "Python" ]] || [[ "$output" =~ "not found" ]]
}

@test "install.sh: fails with old python version" {
    skip_unless_functional

    # Create mock python3 that reports old version
    local temp_bin="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$temp_bin"
    cat > "$temp_bin/python3" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *"version_info"* ]]; then
    echo "3.9"
else
    exit 1
fi
EOF
    chmod +x "$temp_bin/python3"

    export PATH="$temp_bin:/usr/bin:/bin"

    cd "$BATS_TEST_TMPDIR"
    cp "$INSTALL_SCRIPT" .
    # Create fake pyproject.toml so we pass that check
    echo "[project]" > pyproject.toml

    run bash install.sh

    [ "$status" -ne 0 ]
    [[ "$output" =~ "3.11" ]] || [[ "$output" =~ "required" ]]
}

@test "install.sh: fails without pyproject.toml" {
    skip_unless_functional

    cd "$BATS_TEST_TMPDIR"
    cp "$INSTALL_SCRIPT" .
    # Don't create pyproject.toml

    run bash install.sh

    [ "$status" -ne 0 ]
    [[ "$output" =~ "pyproject.toml" ]]
}

@test "install.sh: handles pip install failure" {
    skip_unless_functional

    # Create mock python3 that passes version check but fails pip
    local temp_bin="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$temp_bin"
    cat > "$temp_bin/python3" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *"version_info"* ]]; then
    echo "3.11"
elif [[ "$*" == *"pip"* ]]; then
    echo "pip install failed" >&2
    exit 1
else
    exit 0
fi
EOF
    chmod +x "$temp_bin/python3"

    export PATH="$temp_bin:/usr/bin:/bin"

    cd "$BATS_TEST_TMPDIR"
    cp "$INSTALL_SCRIPT" .
    echo "[project]" > pyproject.toml

    run bash install.sh

    # Should fail due to pip install failure
    [ "$status" -ne 0 ]
}

@test "install.sh: warns when not in git repository" {
    skip_unless_functional

    # Create mock that passes python checks
    local temp_bin="$BATS_TEST_TMPDIR/bin"
    mkdir -p "$temp_bin"

    # Mock python3 to pass version check but skip pip
    cat > "$temp_bin/python3" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *"version_info"* ]]; then
    echo "3.11"
elif [[ "$*" == *"pip"* ]]; then
    echo "Dependencies installed"
    exit 0
else
    exit 0
fi
EOF
    chmod +x "$temp_bin/python3"

    # Mock git to fail rev-parse (not a repo)
    cat > "$temp_bin/git" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "rev-parse" ]]; then
    exit 128
fi
exit 0
EOF
    chmod +x "$temp_bin/git"

    export PATH="$temp_bin:/usr/bin:/bin"

    cd "$BATS_TEST_TMPDIR"
    cp "$INSTALL_SCRIPT" .
    echo "[project]" > pyproject.toml

    run bash install.sh

    # Should warn about not being a git repo
    [[ "$output" =~ "Not a git repository" ]] || [[ "$output" =~ "git" ]]
}
