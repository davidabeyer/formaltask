#!/bin/bash
# PostSlashCommand validation hook
# Validates critical FormalTask commands completed all required steps

set -euo pipefail

# Read hook data from stdin
HOOK_DATA=$(cat)

# Extract command
COMMAND=$(echo "$HOOK_DATA" | jq -r '.command // ""')

# Only validate pm: commands
if [[ ! "$COMMAND" =~ ^/pm- ]]; then
  echo '{"allowed": true}'
  exit 0
fi

# Get git root (works in worktrees)
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$GIT_ROOT" ]; then
  echo '{"allowed": true}'
  exit 0
fi

# Validation based on command
case "$COMMAND" in
  /pm-epic-sync*)
    # Extract epic name
    EPIC_NAME=$(echo "$COMMAND" | sed 's|^/pm-epic-sync ||')

    # Check if worktree was created
    if ! git worktree list | grep -q "epic-$EPIC_NAME"; then
      echo "{\"allowed\": false, \"reason\": \"❌ VALIDATION FAILED: /pm-epic-sync did not create worktree\\n\\nExpected: ../epic-$EPIC_NAME\\n\\nFix: git worktree add ../epic-$EPIC_NAME epic/$EPIC_NAME\\n\\nThis is critical for FormalTask workflow.\"}"
      exit 0
    fi

    # Check if github-mapping.md was created
    if [ ! -f "$GIT_ROOT/.claude/epics/$EPIC_NAME/github-mapping.md" ]; then
      echo "{\"allowed\": false, \"reason\": \"❌ VALIDATION FAILED: /pm-epic-sync did not create github-mapping.md\\n\\nExpected: .claude/epics/$EPIC_NAME/github-mapping.md\\n\\nThis indicates GitHub sync may have failed.\"}"
      exit 0
    fi
    ;;
esac

# All validations passed
echo '{"allowed": true}'
exit 0
