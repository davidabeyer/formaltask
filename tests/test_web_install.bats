#!/usr/bin/env bats

# Task #2813: Tests for web-install.sh one-liner installer
# TDD: Tests written BEFORE implementation

# Get the project root (where scripts/web-install.sh should be)
PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
WEB_INSTALL_SCRIPT="$PROJECT_ROOT/scripts/web-install.sh"

# ============================================================================
# Script Existence and Basic Structure
# ============================================================================

@test "web-install.sh exists" {
    [[ -f "$WEB_INSTALL_SCRIPT" ]]
}

@test "web-install.sh is executable" {
    [[ -x "$WEB_INSTALL_SCRIPT" ]]
}

@test "web-install.sh uses set -euo pipefail for safety" {
    run grep -E '^set -euo pipefail' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh syntax is valid" {
    run bash -n "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh passes shellcheck" {
    if ! command -v shellcheck &>/dev/null; then
        skip "shellcheck not installed"
    fi
    run shellcheck "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

# ============================================================================
# Platform Detection
# ============================================================================

@test "web-install.sh detects unsupported OS and exits with error" {
    # Script should contain case statement that exits on unsupported OS
    run grep -A5 'case.*OS' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
    run grep 'exit 1' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh supports Darwin (macOS)" {
    run grep -E 'Darwin.*PLATFORM.*macos|Darwin.*macos' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh supports Linux" {
    run grep -E 'Linux.*PLATFORM.*linux|Linux.*linux' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh shows error for unsupported OS" {
    run grep -E "Unsupported.*OS|Unsupported:" "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

# ============================================================================
# Python Check
# ============================================================================

@test "web-install.sh checks for python3" {
    run grep 'command -v python3' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh shows macOS remediation for missing python" {
    run grep -E 'brew install.*python' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh shows Linux remediation for missing python" {
    run grep -E 'apt install.*python|apt-get install.*python' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

# ============================================================================
# Directory Structure
# ============================================================================

@test "web-install.sh creates .formaltask directory in HOME" {
    run grep -E 'INSTALL_DIR.*HOME.*formaltask|\$HOME/.formaltask' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh clones git repository" {
    run grep 'git clone' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh creates venv" {
    run grep 'python3 -m venv' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

# ============================================================================
# Wrapper Script
# ============================================================================

@test "web-install.sh creates bin directory" {
    run grep 'mkdir.*bin' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh creates ft wrapper script" {
    run grep -E 'bin/ft|ft.*wrapper' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh wrapper activates venv" {
    run grep 'venv/bin/activate' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh makes wrapper executable" {
    run grep -E 'chmod.*\+x.*bin/ft' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

# ============================================================================
# PATH Modification (Idempotent)
# ============================================================================

@test "web-install.sh detects shell type from SHELL variable" {
    run grep 'case.*SHELL' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh supports bash shell rc" {
    run grep '.bashrc' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh supports zsh shell rc" {
    run grep '.zshrc' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh supports fish shell config" {
    run grep 'config.fish' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh PATH modification is idempotent (uses grep -qF)" {
    # Should check if line already exists before adding
    run grep 'grep -qF' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

@test "web-install.sh shows restart/source instructions" {
    run grep -E 'source.*RC_FILE|Restart shell' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

# ============================================================================
# Installation Steps
# ============================================================================

@test "web-install.sh runs install.sh after cloning" {
    run grep './install.sh' "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
}

# ============================================================================
# Functional Tests (run in Docker containers)
# ============================================================================
# These tests actually execute the installer and verify results.
# Skip unless RUN_FUNCTIONAL_TESTS=1 (set in Docker test environment)

skip_unless_functional() {
    if [[ "${RUN_FUNCTIONAL_TESTS:-}" != "1" ]]; then
        skip "Functional tests disabled (set RUN_FUNCTIONAL_TESTS=1 to enable)"
    fi
}

functional_setup() {
    # Clean state before each functional test
    rm -rf "$HOME/.formaltask"
    # Create empty shell rc file if needed
    touch "$HOME/.bashrc"
}

functional_teardown() {
    # Clean up after functional tests
    rm -rf "$HOME/.formaltask"
}

@test "[functional] web-install.sh creates directory structure" {
    skip_unless_functional
    functional_setup

    run bash "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]

    [[ -d "$HOME/.formaltask/src" ]]
    [[ -d "$HOME/.formaltask/venv" ]]
    [[ -d "$HOME/.formaltask/bin" ]]

    functional_teardown
}

@test "[functional] ft wrapper exists and is executable" {
    skip_unless_functional
    functional_setup

    run bash "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]

    [[ -x "$HOME/.formaltask/bin/ft" ]]

    functional_teardown
}

@test "[functional] ft wrapper activates venv and runs --help" {
    skip_unless_functional
    functional_setup

    run bash "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]

    run "$HOME/.formaltask/bin/ft" --help
    [[ "$status" -eq 0 ]]
    # Should show help output
    [[ "$output" == *"usage"* ]] || [[ "$output" == *"Usage"* ]] || [[ "$output" == *"help"* ]]

    functional_teardown
}

@test "[functional] ft doctor passes after install" {
    skip_unless_functional
    functional_setup

    run bash "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]

    run "$HOME/.formaltask/bin/ft" doctor
    # doctor may exit 0 or report issues but shouldn't crash
    [[ "$status" -eq 0 ]] || [[ "$status" -eq 1 ]]

    functional_teardown
}

@test "[functional] PATH line added to shell rc" {
    skip_unless_functional
    functional_setup

    # Start with empty .bashrc
    echo "" > "$HOME/.bashrc"

    SHELL=/bin/bash run bash "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]

    # Verify PATH modification was added
    run grep -q ".formaltask/bin" "$HOME/.bashrc"
    [[ "$status" -eq 0 ]]

    functional_teardown
}

@test "[functional] PATH modification is idempotent" {
    skip_unless_functional
    functional_setup

    echo "" > "$HOME/.bashrc"

    # Run twice
    SHELL=/bin/bash run bash "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]
    SHELL=/bin/bash run bash "$WEB_INSTALL_SCRIPT"
    [[ "$status" -eq 0 ]]

    # Should only have one PATH line
    count=$(grep -c ".formaltask/bin" "$HOME/.bashrc" || echo "0")
    [[ "$count" -eq 1 ]]

    functional_teardown
}
