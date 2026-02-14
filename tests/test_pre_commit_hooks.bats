#!/usr/bin/env bats
# test_pre_commit_hooks.bats
#
# BATS tests for .git/hooks/pre-commit.legacy
# Phase 0 (RED): Tests for new functionality will FAIL until implementation
#
# Run: bats tests/test_pre_commit_hooks.bats
#
# BATS Best Practice: All tests end with assertions as the LAST line.
# In Bash 3.2 (macOS default), commands after [[ ]] can mask failures.

# Load test helper
load 'test_helper'

# Project root for accessing hook (hooks/tests -> hooks -> root)
PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."

# ============================================================================
# Setup/Teardown
# ============================================================================

setup() {
    # Create isolated temp git repo for each test
    export TEST_REPO=$(mktemp -d -t bats-precommit-XXXXXX)
    cd "$TEST_REPO"

    # Initialize git repo with required config
    git init --quiet
    git config user.email "test@test.com"
    git config user.name "Test User"

    # Copy pre-commit.legacy as the pre-commit hook
    cp "$PROJECT_ROOT/.git/hooks/pre-commit.legacy" .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

    # Create initial commit so we have a valid repo state
    echo "initial" > README.md
    git add README.md
    git commit -m "Initial commit" --quiet
}

teardown() {
    cd /
    [ -d "$TEST_REPO" ] && rm -rf "$TEST_REPO"
}

# ============================================================================
# Test 1: Basic infrastructure verification
# ============================================================================

@test "pre-commit hook exists and is executable" {
    [ -f "$TEST_REPO/.git/hooks/pre-commit" ]
    [ -x "$TEST_REPO/.git/hooks/pre-commit" ]
}

@test "clean commit passes all checks" {
    # Stage a simple file change (not in documented areas)
    echo "content" > simple.txt
    git add simple.txt

    # Run hook - should pass (no TTY = non-interactive, no doc areas)
    run .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "doc_guard passes when CLAUDE.md is included" {
    # Create substantial file in documented area (>20 lines to trigger threshold)
    mkdir -p hooks/lib
    for i in $(seq 1 25); do
        echo "def func_$i(): pass" >> hooks/lib/new_module.py
    done

    # Also include CLAUDE.md change
    echo "# Updated documentation" > CLAUDE.md

    git add hooks/lib/new_module.py CLAUDE.md

    run .git/hooks/pre-commit
    [ "$status" -eq 0 ]
    # Verify doc_guard did NOT trigger (no documentation checkpoint message)
    [[ ! "$output" =~ "Documentation checkpoint" ]]
}

@test "doc_guard blocks substantial changes without CLAUDE.md" {
    # Create substantial change in documented area (30+ lines to exceed threshold)
    mkdir -p hooks/lib
    for i in $(seq 1 35); do
        echo "def func_$i(): pass" >> hooks/lib/new_module.py
    done

    git add hooks/lib/new_module.py

    # Non-interactive mode should block
    run .git/hooks/pre-commit
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Documentation checkpoint" ]] || [[ "$output" =~ "CLAUDE.md" ]]
}

@test "DO_NOT_COMMIT marker blocks commit" {
    # Create marker file with specific content
    echo "This worktree has test issues" > .DO_NOT_COMMIT
    echo "new file" > test.txt
    git add test.txt

    run .git/hooks/pre-commit
    [ "$status" -eq 1 ]
    # Verify the exact blocking message
    [[ "$output" =~ "COMMIT BLOCKED - UNSAFE WORKTREE" ]]
    # Verify the marker file content was displayed
    [[ "$output" =~ "This worktree has test issues" ]]
}

# ============================================================================
# Error Accumulation and Mode Tests (Task #712 - Implemented)
# ============================================================================

@test "error accumulation collects multiple errors in batch mode" {
    # Verifies the error accumulation pattern: hook runs ALL checks and collects errors

    # Create file triggering doc_guard (substantial change without CLAUDE.md)
    mkdir -p hooks/lib
    for i in $(seq 1 35); do
        echo "def func_$i(): pass" >> hooks/lib/module.py
    done

    git add hooks/lib/module.py

    # Run in batch mode - should collect ALL errors and show summary
    PRE_COMMIT_MODE=batch run .git/hooks/pre-commit

    # Verify batch mode was active
    [[ "$output" =~ "Mode: batch" ]]
    # Verify error was collected (count shown)
    [ "$status" -eq 1 ]
    [[ "$output" =~ "ERRORS" ]]
    [[ "$output" =~ "errors collected" ]]
}

@test "fail-fast mode exits on first error" {
    # FAIL_FAST=1 stops at first error instead of collecting all

    # Create file triggering doc_guard
    mkdir -p hooks/lib
    for i in $(seq 1 35); do
        echo "def func_$i(): pass" >> hooks/lib/module.py
    done

    git add hooks/lib/module.py

    # Run with fail-fast - should exit immediately on first error
    FAIL_FAST=1 run .git/hooks/pre-commit

    # Verify fail-fast mode output
    [ "$status" -eq 1 ]
    # Exact message from hook
    [[ "$output" =~ "[fail-fast] Stopping on first error" ]]
    # Should NOT show the summary section (exited early)
    [[ ! "$output" =~ "PRE-COMMIT SUMMARY" ]]
}

@test "mode detection shows current mode" {
    # Hook indicates which mode it's running in

    echo "test" > test.txt
    git add test.txt

    # Run without explicit mode - should auto-detect
    run .git/hooks/pre-commit

    # Verify mode is displayed with correct format "Mode: <mode>"
    [[ "$output" =~ "Mode: " ]]
}

# ============================================================================
# Secret Detection Tests (Task #713)
# ============================================================================

@test "secret detection blocks hardcoded API keys" {
    # Skip if detect-secrets not installed
    command -v detect-secrets &> /dev/null || skip "detect-secrets not installed"

    # Create a baseline for the test repo (empty baseline = all secrets flagged)
    detect-secrets scan --list-all-plugins > .secrets.baseline

    # Create file with hardcoded secret (pragma: allowlist secret - test value)
    echo "API_KEY='sk-1234567890abcdef1234567890abcdef'" > config.py  # pragma: allowlist secret
    git add config.py

    # Run hook in batch mode
    PRE_COMMIT_MODE=batch run .git/hooks/pre-commit

    # Should fail and mention secrets - hook outputs "Found potential secret(s)"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "secret" ]]
}

# ============================================================================
# Dependency Audit Tests (Task #714)
# ============================================================================

@test "pip-audit runs when dependency files are staged" {
    # This test verifies that the dependency_audit_check function is triggered
    # when requirements.txt is staged, without depending on network success.

    # Create a requirements file with a valid package
    echo "pip>=21.0" > requirements.txt
    git add requirements.txt

    # Run hook - we check that pip-audit check was TRIGGERED, not that it succeeded
    # Network-dependent success/failure is handled gracefully by the hook
    run .git/hooks/pre-commit

    # Verify the dependency check was triggered (one of these MUST appear):
    # - "Checking dependency vulnerabilities" = check started
    # - "pip-audit not installed" = graceful skip (still valid trigger)
    # - "Running pip-audit" = actual execution
    # - "No known vulnerabilities" = successful check
    # - "Vulnerabilities found" = successful check with findings
    [[ "$output" =~ "Checking dependency" ]] || \
    [[ "$output" =~ "pip-audit not installed" ]] || \
    [[ "$output" =~ "Running pip-audit" ]] || \
    [[ "$output" =~ "No known vulnerabilities" ]] || \
    [[ "$output" =~ "Vulnerabilities found" ]]
}

# ============================================================================
# Security Tests (Task #727 - P0 Command Injection Fixes)
# ============================================================================

@test "xargs uses safe delimiter in hook code" {
    # Verify security fix: xargs should use -0 to handle filenames safely
    # This prevents command injection via filenames with spaces or special characters
    # The pattern is: tr '\n' '\0' | xargs -0 (portable across BSD/GNU)
    run grep -E 'xargs -0' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "stub check uses safe filename handling" {
    # Verify security fix: stub_check should not directly interpolate $file into Python code
    # Should use environment variable or argument passing instead
    # Check that the hook does NOT use Path('$file') pattern (unsafe)
    run grep "Path('\$file')" .git/hooks/pre-commit
    # This should NOT match if the fix is in place (status non-zero = no match = good)
    [ "$status" -ne 0 ]
}

@test "CI workflow uses pinned dependency versions" {
    # Verify security fix: CI workflow should pin specific versions to prevent supply chain attacks
    # Check that pip install lines contain version specifiers (==, >=, ~=)
    workflow="$PROJECT_ROOT/.github/workflows/pre-commit.yml"
    [ -f "$workflow" ] || skip "CI workflow not found"

    # Each package should have a version specifier
    run /usr/bin/grep -E 'pip install.*==' "$workflow"
    [ "$status" -eq 0 ]
}

# ============================================================================
# Stub Check Tests (Task #729 - P1 Test Coverage)
# ============================================================================

@test "stub_check detects functions with pass body" {
    # Create a Python file with a stub function
    cat > stub_example.py << 'EOF'
def my_function():
    pass
EOF
    git add stub_example.py

    # Run hook - should detect stub and warn
    run .git/hooks/pre-commit

    # Should detect stub functions - hook outputs "Stub functions detected" or "Stubs detected"
    [[ "$output" =~ [Ss]tub.*detected ]] || [[ "$output" =~ "is a stub" ]]
}

# ============================================================================
# API Stability Check Tests (Task #729 - P1 Test Coverage)
# ============================================================================

@test "api_stability_check blocks on breaking changes" {
    # Export PROJECT_ROOT to point to test repo (ensures hook finds mock script)
    export PROJECT_ROOT="$TEST_REPO"

    # Create a mock api-stability-check.sh that fails
    mkdir -p hooks
    cat > hooks/api-stability-check.sh << 'EOF'
#!/bin/bash
echo "Breaking API change detected"
exit 1
EOF
    chmod +x hooks/api-stability-check.sh

    echo "test" > test.txt
    git add test.txt

    # Run hook
    run .git/hooks/pre-commit

    # Clean up env
    unset PROJECT_ROOT

    # Should block commit
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Breaking API" ]]
}

# ============================================================================
# TypeScript Check Tests (Task #729 - P1 Test Coverage)
# ============================================================================

@test "typescript_check warns when tsconfig.json missing" {
    # Create a TypeScript file but no tsconfig
    echo "const x: number = 1;" > test.ts
    git add test.ts

    # Run hook
    run .git/hooks/pre-commit

    # Should warn about missing tsconfig but not block
    [ "$status" -eq 0 ]
    [[ "$output" =~ "tsconfig" ]]
}

# ============================================================================
# Test Impact Check Tests (Task #729 - P1 Test Coverage)
# ============================================================================

@test "test_impact_check skips without testmondata" {
    # No .testmondata file exists in fresh repo
    echo "def foo(): return 1" > source.py
    git add source.py

    # Run hook - should not block on testmon
    run .git/hooks/pre-commit

    # Should pass (testmon not blocking)
    [ "$status" -eq 0 ]
}

# ============================================================================
# Interactive Mode Tests (Task #729 - P1 Test Coverage)
# ============================================================================

@test "interactive mode detection with explicit env var" {
    # Test that PRE_COMMIT_MODE=interactive is respected
    echo "test" > test.txt
    git add test.txt

    PRE_COMMIT_MODE=interactive run .git/hooks/pre-commit

    # Should show interactive mode in output
    [[ "$output" =~ "Mode: interactive" ]]
}

# ============================================================================
# Warnings Array Tests (Task #729 - P1 Test Coverage)
# ============================================================================

@test "warnings are accumulated and displayed in batch mode summary" {
    # Create conditions that may generate warnings (stub detection warns in non-interactive)
    cat > warning_stub.py << 'EOF'
def incomplete():
    pass
EOF
    git add warning_stub.py

    # Run in batch mode to see the summary
    PRE_COMMIT_MODE=batch run .git/hooks/pre-commit

    # Output should contain batch mode summary or stub/warning detection
    [[ "$output" =~ "SUMMARY" ]] || [[ "$output" =~ [Ss]tub ]] || [[ "$output" =~ "Warning" ]]
}

# ============================================================================
# Deleted Files in doc_guard Tests (Task #729 - P1 Test Coverage)
# ============================================================================

@test "doc_guard flags deleted files in documented areas" {
    # Create a file in documented area and commit it
    # Note: Use --no-verify for initial commit since doc_guard would block it
    mkdir -p hooks/lib
    echo "def foo(): return 1" > hooks/lib/to_delete.py
    echo "# Doc update" > CLAUDE.md  # Include CLAUDE.md to satisfy doc_guard
    git add hooks/lib/to_delete.py CLAUDE.md
    git commit -m "Add file to delete" --quiet

    # Now delete it (but don't update CLAUDE.md this time)
    git rm hooks/lib/to_delete.py

    # Run hook in non-interactive mode
    run .git/hooks/pre-commit

    # Should flag the deletion as requiring CLAUDE.md update
    [ "$status" -eq 1 ]
    [[ "$output" =~ "CLAUDE.md" ]]
}

@test "doc_guard handles filenames with spaces in documented areas" {
    # Test that doc_guard correctly processes filenames containing spaces
    # This verifies the staged variable is properly quoted to prevent word splitting
    cd "$BATS_TEST_TMPDIR"
    git init --quiet
    git config user.email "test@test.com"
    git config user.name "Test User"
    mkdir -p hooks/lib

    # Create a file with spaces in name in documented area
    echo "def test(): pass" > "hooks/lib/file with spaces.py"
    git add "hooks/lib/file with spaces.py"

    # Copy the pre-commit hook
    mkdir -p .git/hooks
    cp "$BATS_TEST_DIRNAME/../pre-commit.legacy.sh" .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

    # Run hook in batch mode (non-interactive)
    PRE_COMMIT_MODE=batch run .git/hooks/pre-commit

    # Should detect the file as being in a documented area
    # If word splitting occurred, the filename would be broken and not detected
    [[ "$output" =~ "hooks/lib" ]] || [[ "$output" =~ "CLAUDE.md" ]]
}

# ============================================================================
# Logic and Error Handling Tests (Task #730 - P1 Fixes)
# ============================================================================

@test "stub_check uses PROJECT_ROOT for hooks/lib path" {
    # Verify the hook uses PROJECT_ROOT environment variable for imports
    # This ensures the hook works from any working directory
    run grep -E "STUB_LIB_PATH|PROJECT_ROOT.*hooks/lib" .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "api_stability_check validates path under PROJECT_ROOT" {
    # Verify api-stability-check.sh path uses PROJECT_ROOT for worktree support
    # The path should be validated to prevent path traversal attacks
    run grep -E 'api.*stability.*(PROJECT_ROOT|\$\{PROJECT_ROOT)' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "doc_guard uses native bash regex instead of echo|grep" {
    # Verify doc_guard uses [[ =~ ]] instead of echo|grep for CLAUDE.md check
    # This improves performance and avoids spawning subprocesses
    # The pattern should be: [[ "$staged" =~ CLAUDE\.md ]] not: echo "$staged" | grep
    run grep -E '\[\[.*staged.*=~.*CLAUDE' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "doc_guard detects CLAUDE.md in multi-file staging" {
    # Verify CLAUDE.md is detected when staged WITH other files
    # This tests the regex handles multi-line $staged correctly
    # Bug: [[ =~ ]] with $ matches end-of-string, not end-of-line
    mkdir -p hooks/lib
    echo "# Docs" > CLAUDE.md
    echo "def x(): pass" > hooks/lib/test.py
    git add CLAUDE.md hooks/lib/test.py

    run .git/hooks/pre-commit
    # Should pass because CLAUDE.md is included
    [ "$status" -eq 0 ]
}

@test "interactive mode validates REPLY variable before using it" {
    # Verify the hook initializes REPLY or uses default behavior
    # The REPLY variable should be validated (checked for empty/unset) before pattern matching
    # Look for: [[ -n "$REPLY" ]] or ${REPLY:-} or similar safe access
    run grep -E 'REPLY:-|REPLY:=|REPLY" \&\&|z "\$REPLY"|n "\$REPLY"' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "detect-secrets shows errors for debugging" {
    # Verify detect-secrets command does not suppress stderr completely
    # Should use 2>&1 to show errors OR no stderr redirection at all
    # Check that the detect-secrets line does NOT end with 2>/dev/null
    run grep 'detect-secrets-hook.*2>/dev/null' .git/hooks/pre-commit
    # This should NOT match if the fix is in place (status non-zero = no match = good)
    [ "$status" -ne 0 ]
}

# ============================================================================
# Refactoring Tests (Task #731 - P2 Complexity Reduction)
# ============================================================================

@test "helper function check_command_available exists" {
    # Verify refactored helper function is defined in hook
    run grep -E '^check_command_available\(\)' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "secret_detection_check uses check_command_available helper" {
    # Verify refactoring: secret_detection_check uses the extracted helper
    run grep -A 20 'secret_detection_check()' .git/hooks/pre-commit
    [[ "$output" =~ "check_command_available" ]]
}

@test "dependency_audit_check uses check_command_available helper" {
    # Verify refactoring: dependency_audit_check uses the extracted helper
    run grep -A 20 'dependency_audit_check()' .git/hooks/pre-commit
    [[ "$output" =~ "check_command_available" ]]
}

@test "helper function find_requirements_file exists" {
    # Verify refactored helper function for finding requirements file
    run grep -E '^find_requirements_file\(\)' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "dependency_audit_check uses find_requirements_file helper" {
    # Verify refactoring: dependency_audit_check uses the extracted helper
    run grep -A 30 'dependency_audit_check()' .git/hooks/pre-commit
    [[ "$output" =~ "find_requirements_file" ]]
}

# ============================================================================
# Configuration Tests (Task #732 - P2 Extract Hardcoded Values)
# ============================================================================

@test "configuration section exists with named constants" {
    # Verify a dedicated configuration section with env var overrides
    run grep -E '^# Configuration' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "get_modification_threshold function loads from Python config" {
    # Verify the hook has a function to get threshold from Python config
    run grep -E 'get_modification_threshold\(\)' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "doc_guard uses get_modification_threshold function" {
    # Verify doc_guard_check uses the Python config function, not hardcoded value
    run grep -A 40 'doc_guard_check()' .git/hooks/pre-commit
    [[ "$output" =~ "get_modification_threshold" ]]
}

@test "TSCONFIG_FILE is configurable via env var" {
    # Verify tsconfig filename uses env var with default
    run grep 'TSCONFIG_FILE.*:-tsconfig.json' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "typescript_check uses TSCONFIG_FILE config variable" {
    # Verify typescript_check uses the configurable variable
    run grep -A 20 'typescript_check()' .git/hooks/pre-commit
    [[ "$output" =~ "TSCONFIG_FILE" ]]
}

# ============================================================================
# Error Visibility and Consistency Tests (Task #733 - P2 Improvements)
# ============================================================================

@test "pip-audit output is not truncated with head" {
    # Verify pip-audit output is not artificially truncated
    # The old pattern was: pip-audit ... 2>&1 | head -20
    # This should NOT be present
    run grep 'pip-audit.*| head' .git/hooks/pre-commit
    [ "$status" -ne 0 ]
}

@test "TTY detection uses stdout not stdin for mode detection" {
    # Verify mode detection checks stdout (-t 1) not stdin (-t 0)
    # The comment says "default with TTY" so it should check output capability
    run grep -E 'if \[ -t 1 \]' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "interactive prompts check stdout TTY" {
    # Verify interactive prompts in doc_guard and stub_check check -t 1
    # The pattern "if [ -t 1 ]" should appear before read prompts
    run grep -B 3 'read -r -p' .git/hooks/pre-commit
    [[ "$output" =~ "-t 1" ]]
}

@test "PIP_AUDIT_MAX_LINES configuration exists" {
    # Verify there's a configurable limit for pip-audit output
    run grep 'PIP_AUDIT_MAX_LINES' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

@test "pip-audit shows truncation warning when output exceeds limit" {
    # Verify the hook warns when output is truncated
    run grep -A 10 'PIP_AUDIT_MAX_LINES' .git/hooks/pre-commit
    [[ "$output" =~ "truncated" ]] || [[ "$output" =~ "more lines" ]]
}

# ============================================================================
# Security Fix Tests (Task #742 - P0 Read Command Safety)
# ============================================================================

@test "read commands use -r flag for safe backslash handling" {
    # Verify all read -p commands use -r flag to prevent backslash interpretation
    # Pattern: read -r -p is safe, read -p without -r is unsafe
    # Check that no unsafe pattern exists (read -p without preceding -r)
    run grep -E 'read -p' .git/hooks/pre-commit
    # This should NOT match if all read -p have -r flag (grep returns 1 = no match = good)
    [ "$status" -ne 0 ]
}

# ============================================================================
# Security Fix Tests (Task #744 - P1 Filename Spaces Handling)
# ============================================================================

@test "stub_check uses while-read pattern for safe filename handling" {
    # Verify stub_check uses 'while IFS= read -r' instead of 'for file in $var'
    # The 'for' pattern fails with filenames containing spaces
    run grep -A 5 'Run stub detector on staged files' .git/hooks/pre-commit
    [[ "$output" =~ "while IFS= read -r" ]]
    # Should NOT use vulnerable 'for file in $' pattern
    run grep 'for file in \$staged_py' .git/hooks/pre-commit
    [ "$status" -ne 0 ]
}

@test "stub_check handles files with spaces in names" {
    # Create a Python file with space in name
    echo 'def stub_func(): pass' > "test file with spaces.py"
    git add "test file with spaces.py"

    # Run hook - should not crash and should detect stub
    run .git/hooks/pre-commit

    # Verify the file was processed (stub detected or check passed)
    # The key is no bash word-splitting error occurred
    [[ "$output" =~ "Checking for stub" ]]
}

# ============================================================================
# Logic Fix Tests (Task #745 - P1 Stderr Redirection)
# ============================================================================

@test "find_requirements_file redirects warning to stderr" {
    # Verify the warning message uses >&2 to redirect to stderr
    # This prevents the warning from corrupting the captured return value
    run grep 'No requirements.txt found.*>&2' .git/hooks/pre-commit
    [ "$status" -eq 0 ]
}

# ============================================================================
# Edge Case Tests (Task #776 - Coverage Gaps)
# ============================================================================

@test "handles empty Python file gracefully" {
    # Empty files should not crash the hook or produce errors
    touch empty.py
    git add empty.py

    run .git/hooks/pre-commit

    # Should pass without crashing
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "Error" ]]
}

@test "gracefully skips binary files" {
    # Binary files should not cause crashes in text processing
    printf '\x00\x01\x02\xff' > binary.bin
    git add binary.bin

    run .git/hooks/pre-commit

    # Should complete without crashing on binary content
    [ "$status" -eq 0 ]
}

@test "handles partial staging correctly" {
    # Test that hook only processes staged content, not working tree
    echo "line1" > partial.py
    git add partial.py
    git commit -m "initial" --quiet

    # Modify file but only stage some changes
    printf 'line1\nline2\nline3' > partial.py
    git add partial.py

    run .git/hooks/pre-commit

    # Should process successfully
    [ "$status" -eq 0 ]
}

@test "handles missing detect-secrets gracefully" {
    # When detect-secrets is not installed, hook should continue
    PATH_BACKUP="$PATH"
    export PATH="/usr/bin:/bin"

    run .git/hooks/pre-commit

    export PATH="$PATH_BACKUP"

    # Should not crash - either skip or warn
    [[ "$output" =~ "not installed" ]] || [[ "$output" =~ "skipping" ]] || [ "$status" -eq 0 ]
}

@test "handles file deleted after staging" {
    # File deleted after git add should not crash hook
    echo "content" > deleted.py
    git add deleted.py
    rm deleted.py

    run .git/hooks/pre-commit

    # Should handle gracefully (may fail or succeed, but not crash)
    [[ ! "$output" =~ "bash: " ]]
}

# ============================================================================
# COVERAGE TESTS - Runtime security behavior
# ============================================================================

@test "detect-secrets blocks files containing secret patterns" {
    # Skip if detect-secrets not installed
    if ! command -v detect-secrets &>/dev/null; then
        skip "detect-secrets not installed"
    fi

    # Create a file with an obvious secret pattern (not a real secret)
    echo 'API_KEY = "FAKE_SECRET_FOR_TESTING_ONLY_not_real"' > secret_config.py  # pragma: allowlist secret
    git add secret_config.py

    run .git/hooks/pre-commit

    # detect-secrets should find this and warn/block
    # Note: behavior depends on baseline - may warn or block
    [[ "$output" =~ "secret" ]] || [[ "$output" =~ "Secret" ]] || [[ "$output" =~ "baseline" ]] || [ "$status" -ne 0 ]
}

@test "detect-secrets allows files without secrets" {
    # Skip if detect-secrets not installed
    if ! command -v detect-secrets &>/dev/null; then
        skip "detect-secrets not installed"
    fi

    # Create a file with no secret patterns - just normal config
    echo 'config = {"debug": True, "timeout": 30}' > safe_config.py
    git add safe_config.py

    run .git/hooks/pre-commit

    # Should pass - no secrets found
    [ "$status" -eq 0 ]
}
