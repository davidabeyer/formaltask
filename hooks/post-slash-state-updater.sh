#!/bin/bash
# PostSlashCommand hook state updater
# Updates state.json after successful command execution

set -euo pipefail

# Arguments from hook invocation
COMMAND="${1:-}"
EPIC_NAME="${2:-}"
CLAUDE_DIR="${3:-$HOME/.claude}"

# Paths
EPIC_PATH="${CLAUDE_DIR}/epics/${EPIC_NAME}"
STATE_FILE="${EPIC_PATH}/state.json"

# Ensure epic directory exists
mkdir -p "$EPIC_PATH"

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Helper: Extract GitHub issue number from epic.md frontmatter
get_epic_github_number() {
    local epic_path="$1"
    local epic_file="${epic_path}/epic.md"

    if [ ! -f "$epic_file" ]; then
        return 1
    fi

    # Extract GitHub URL from frontmatter and get issue number
    # Using sed instead of grep -P for macOS compatibility
    grep "^github:.*issues/" "$epic_file" | sed 's|.*issues/||' | sed 's|[^0-9].*||' | head -1
}

# Initialize or update state.json based on command
case "$COMMAND" in
    "/pm-prd-new")
        # Create initial state
        cat > "$STATE_FILE" <<EOF
{
  "epic": "${EPIC_NAME}",
  "phase": "prd",
  "phase_metadata": {
    "worktree_created": false,
    "worktree_path": "../${EPIC_NAME}",
    "github_synced": false,
    "github_epic": null
  },
  "tasks": {"total": 0, "completed": 0},
  "audit": {
    "last_command": "${COMMAND}",
    "last_updated": "${TIMESTAMP}"
  }
}
EOF
        ;;
    
    "/pm-prd-parse")
        # Update phase to planning
        if [[ -f "$STATE_FILE" ]]; then
            jq ".phase = \"planning\" | .audit.last_command = \"${COMMAND}\" | .audit.last_updated = \"${TIMESTAMP}\"" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
        fi
        ;;
    
    "/pm-epic-sync")
        # Update phase to synced and set github_synced
        if [[ -f "$STATE_FILE" ]]; then
            jq ".phase = \"synced\" | .phase_metadata.github_synced = true | .audit.last_command = \"${COMMAND}\" | .audit.last_updated = \"${TIMESTAMP}\"" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
        fi

        # Update GitHub label: status:planning → status:ready
        epic_issue=$(get_epic_github_number "$EPIC_PATH" || true)
        if [[ -n "$epic_issue" ]]; then
            gh issue edit "$epic_issue" --remove-label "status:planning" 2>/dev/null || true
            gh issue edit "$epic_issue" --add-label "status:ready" 2>/dev/null || true
        fi
        ;;
    
    "/pm-task-start")
        # Update phase to in_progress
        if [[ -f "$STATE_FILE" ]]; then
            jq ".phase = \"in_progress\" | .audit.last_command = \"${COMMAND}\" | .audit.last_updated = \"${TIMESTAMP}\"" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
        fi
        ;;
    
    "/pm-epic-review")
        # Update phase to review
        if [[ -f "$STATE_FILE" ]]; then
            jq ".phase = \"review\" | .audit.last_command = \"${COMMAND}\" | .audit.last_updated = \"${TIMESTAMP}\"" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
        fi

        # Update GitHub label: status:ready → status:review
        epic_issue=$(get_epic_github_number "$EPIC_PATH" || true)
        if [[ -n "$epic_issue" ]]; then
            gh issue edit "$epic_issue" --remove-label "status:ready" 2>/dev/null || true
            gh issue edit "$epic_issue" --add-label "status:review" 2>/dev/null || true
        fi
        ;;
    
    "/pm-epic-merge")
        # Update phase to merged
        if [[ -f "$STATE_FILE" ]]; then
            jq ".phase = \"merged\" | .audit.last_command = \"${COMMAND}\" | .audit.last_updated = \"${TIMESTAMP}\"" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
        fi

        # Update GitHub label: status:review → status:completed
        epic_issue=$(get_epic_github_number "$EPIC_PATH" || true)
        if [[ -n "$epic_issue" ]]; then
            gh issue edit "$epic_issue" --remove-label "status:review" 2>/dev/null || true
            gh issue edit "$epic_issue" --add-label "status:completed" 2>/dev/null || true
        fi
        ;;
    
    *)
        # For other commands, just update audit trail
        if [[ -f "$STATE_FILE" ]]; then
            jq ".audit.last_command = \"${COMMAND}\" | .audit.last_updated = \"${TIMESTAMP}\"" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
        fi
        ;;
esac

exit 0
