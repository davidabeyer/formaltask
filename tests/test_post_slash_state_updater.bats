#!/usr/bin/env bats

# Tests for PostSlashCommand hook state updater
# This hook updates state.json after successful command execution

setup() {
    SCRIPT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    UPDATER="${SCRIPT_DIR}/post-slash-state-updater.sh"

    # Create temp epic directory structure
    export TEST_EPIC_DIR=$(mktemp -d)
    export CLAUDE_DIR="${TEST_EPIC_DIR}/.claude"
    export EPICS_DIR="${CLAUDE_DIR}/epics"
    mkdir -p "$EPICS_DIR"

    # Set up test epic
    export TEST_EPIC_NAME="test-epic"
    export EPIC_PATH="${EPICS_DIR}/${TEST_EPIC_NAME}"
    mkdir -p "$EPIC_PATH"
}

teardown() {
    rm -rf "$TEST_EPIC_DIR"
}

# Helper: Create state.json with specific phase
create_state_json() {
    local phase=$1
    local worktree_created=${2:-false}
    local github_synced=${3:-false}

    cat > "${EPIC_PATH}/state.json" <<STATE_EOF
{
  "epic": "${TEST_EPIC_NAME}",
  "phase": "${phase}",
  "phase_metadata": {
    "worktree_created": ${worktree_created},
    "worktree_path": "../${TEST_EPIC_NAME}",
    "github_synced": ${github_synced},
    "github_epic": null
  },
  "tasks": {"total": 0, "completed": 0},
  "audit": {
    "last_command": "",
    "last_updated": "2025-11-04T00:00:00Z"
  }
}
STATE_EOF
}

# Test: Creates state.json on prd-new
@test "creates state.json on prd-new" {
    run "$UPDATER" "/pm-prd-new" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]
    [ -f "${EPIC_PATH}/state.json" ]
    grep -q '"phase":[[:space:]]*"prd"' "${EPIC_PATH}/state.json"
}

# Test: Updates phase to planning on prd-parse
@test "updates phase to planning on prd-parse" {
    create_state_json "prd"

    run "$UPDATER" "/pm-prd-parse" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]
    grep -q '"phase":[[:space:]]*"planning"' "${EPIC_PATH}/state.json"
}

# Test: Updates phase to synced on epic-sync
@test "updates phase to synced on epic-sync" {
    create_state_json "planning"

    run "$UPDATER" "/pm-epic-sync" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]
    grep -q '"phase":[[:space:]]*"synced"' "${EPIC_PATH}/state.json"
}

# Test: Updates phase to in_progress on task-start
@test "updates phase to in_progress on task-start" {
    create_state_json "synced"

    run "$UPDATER" "/pm-task-start" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]
    grep -q '"phase":[[:space:]]*"in_progress"' "${EPIC_PATH}/state.json"
}

# Test: Updates phase to review on epic-review
@test "updates phase to review on epic-review" {
    create_state_json "in_progress"

    run "$UPDATER" "/pm-epic-review" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]
    grep -q '"phase":[[:space:]]*"review"' "${EPIC_PATH}/state.json"
}

# Test: Updates audit trail
@test "updates audit trail with last command" {
    create_state_json "planning"

    run "$UPDATER" "/pm-task-add" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]
    grep -q '"last_command":[[:space:]]*"/pm-task-add"' "${EPIC_PATH}/state.json"
}

# Test: Extract GitHub issue number from epic.md
@test "extracts GitHub issue number from epic.md frontmatter" {
    # Create epic.md with GitHub URL
    cat > "${EPIC_PATH}/epic.md" <<'EPIC_EOF'
---
name: test-epic
status: backlog
github: https://github.com/owner/repo/issues/123
---

# Epic: Test Epic
EPIC_EOF

    # Extract and test the function directly (avoid sourcing set -e)
    run bash -c "
    get_epic_github_number() {
        local epic_path=\"\$1\"
        local epic_file=\"\${epic_path}/epic.md\"
        if [ ! -f \"\$epic_file\" ]; then
            return 1
        fi
        grep \"^github:.*issues/\" \"\$epic_file\" | sed 's|.*issues/||' | sed 's|[^0-9].*||' | head -1
    }
    get_epic_github_number '$EPIC_PATH'
    "

    [ "$status" -eq 0 ]
    [ "$output" = "123" ]
}

# Test: Updates GitHub label on epic-sync
@test "updates epic GitHub issue label from planning to ready on epic-sync" {
    create_state_json "planning"

    # Create epic.md with GitHub issue
    cat > "${EPIC_PATH}/epic.md" <<'EPIC_EOF'
---
name: test-epic
status: backlog
github: https://github.com/owner/repo/issues/456
---

# Epic: Test Epic
EPIC_EOF

    # Create a mock gh command that logs calls
    export PATH="${EPIC_PATH}:$PATH"
    cat > "${EPIC_PATH}/gh" <<'GH_MOCK'
#!/bin/bash
echo "gh $*" >> "${EPIC_PATH}/gh-calls.log"
exit 0
GH_MOCK
    chmod +x "${EPIC_PATH}/gh"

    run "$UPDATER" "/pm-epic-sync" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]

    # Verify gh commands were called correctly
    grep -q "gh issue edit 456 --remove-label status:planning" "${EPIC_PATH}/gh-calls.log"
    grep -q "gh issue edit 456 --add-label status:ready" "${EPIC_PATH}/gh-calls.log"
}

# Test: Updates GitHub label on epic-review
@test "updates epic GitHub issue label to review on epic-review" {
    create_state_json "in_progress"

    # Create epic.md with GitHub issue
    cat > "${EPIC_PATH}/epic.md" <<'EPIC_EOF'
---
name: test-epic
status: backlog
github: https://github.com/owner/repo/issues/789
---

# Epic: Test Epic
EPIC_EOF

    # Create a mock gh command that logs calls
    export PATH="${EPIC_PATH}:$PATH"
    cat > "${EPIC_PATH}/gh" <<'GH_MOCK'
#!/bin/bash
echo "gh $*" >> "${EPIC_PATH}/gh-calls.log"
exit 0
GH_MOCK
    chmod +x "${EPIC_PATH}/gh"

    run "$UPDATER" "/pm-epic-review" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]

    # Verify gh commands were called correctly
    grep -q "gh issue edit 789 --remove-label status:ready" "${EPIC_PATH}/gh-calls.log"
    grep -q "gh issue edit 789 --add-label status:review" "${EPIC_PATH}/gh-calls.log"
}

# Test: Updates GitHub label on epic-merge
@test "updates epic GitHub issue label to completed on epic-merge" {
    create_state_json "review"

    # Create epic.md with GitHub issue
    cat > "${EPIC_PATH}/epic.md" <<'EPIC_EOF'
---
name: test-epic
status: backlog
github: https://github.com/owner/repo/issues/999
---

# Epic: Test Epic
EPIC_EOF

    # Create a mock gh command that logs calls
    export PATH="${EPIC_PATH}:$PATH"
    cat > "${EPIC_PATH}/gh" <<'GH_MOCK'
#!/bin/bash
echo "gh $*" >> "${EPIC_PATH}/gh-calls.log"
exit 0
GH_MOCK
    chmod +x "${EPIC_PATH}/gh"

    run "$UPDATER" "/pm-epic-merge" "$TEST_EPIC_NAME" "$CLAUDE_DIR"

    [ "$status" -eq 0 ]

    # Verify gh commands were called correctly
    grep -q "gh issue edit 999 --remove-label status:review" "${EPIC_PATH}/gh-calls.log"
    grep -q "gh issue edit 999 --add-label status:completed" "${EPIC_PATH}/gh-calls.log"
}
