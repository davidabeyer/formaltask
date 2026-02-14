#!/usr/bin/env bats
# tests/test_readme.bats - TDD tests for README.md documentation

# Test F1: README exists at root
@test "README.md exists at project root" {
    test -f README.md
}

# Test F2: Quick Start section exists with < 5 steps
@test "README.md has Quick Start section" {
    grep -q "## Quick Start" README.md
}

@test "Quick Start has 5 or fewer numbered steps" {
    # Extract Quick Start section and count numbered steps
    # Section ends at next ## heading or EOF
    # Use sed to delete last line (portable across BSD/GNU)
    quick_start=$(sed -n '/^## Quick Start/,/^## /p' README.md | sed '$d')
    step_count=$(echo "$quick_start" | grep -c '^[0-9]\.' || true)
    [[ "$step_count" -le 5 ]]
}

# Test F3: Prerequisites documented
@test "README.md has Prerequisites section" {
    grep -q "## Prerequisites" README.md
}

@test "Prerequisites lists Python 3.11+" {
    grep -qi "python.*3\.11" README.md
}

@test "Prerequisites lists optional dependencies" {
    # Check for mention of optional deps or tui/test/dev extras
    grep -qiE "(optional|tui|test|dev|\[all\])" README.md
}

# Test F4: Configuration documented
@test "README.md has Configuration section" {
    grep -q "## Configuration" README.md
}

@test "Configuration documents settings location" {
    grep -q "~/.claude/settings.json" README.md
}

# Test: References install.sh
@test "README.md references install.sh" {
    grep -q "install.sh" README.md
}

# Test: No TODO/TBD placeholders
@test "README.md has no TODO placeholders" {
    ! grep -qi "TODO" README.md
}

@test "README.md has no TBD placeholders" {
    ! grep -qi "TBD" README.md
}

# Test: No personal paths
@test "README.md has no personal paths" {
    ! grep -qE "/Users/[a-z]+/" README.md
}

# Test: All code blocks have language specified
@test "All code blocks have language specified" {
    # Code blocks come in pairs: opening (```language) and closing (```)
    # Count opening blocks with language vs bare closing markers
    # If all opening blocks have language, counts should match
    with_lang=$(grep -c '^```[a-z]' README.md || true)
    without_lang=$(grep -c '^```$' README.md || true)
    [[ "$with_lang" -eq "$without_lang" ]]
}

# Test: Bash commands are copy-pasteable (no leading $ or #)
@test "Bash code blocks have no leading prompt characters" {
    # Extract bash code blocks and check for leading $ or # (comments OK for explanation)
    # This checks that actual command lines don't have $ prefix
    bash_blocks=$(sed -n '/```bash/,/```/p' README.md | grep -v '```' | grep -v '^#' || true)
    # Check none start with $ followed by space (command prompt)
    ! echo "$bash_blocks" | grep -q '^\$ '
}

# Test: Has Installation section
@test "README.md has Installation section" {
    grep -q "## Installation" README.md
}

# Test: Has License section
@test "README.md has License section" {
    grep -qiE "## License|MIT" README.md
}
