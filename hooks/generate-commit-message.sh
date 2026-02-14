#!/bin/bash
# Generate commit message from issue details and agent reports

set -euo pipefail

# Arguments
ISSUE_NUM="${1:-}"
ISSUE_TITLE="${2:-}"
EPIC_DIR="${3:-}"

if [[ -z "$ISSUE_NUM" ]] || [[ -z "$ISSUE_TITLE" ]]; then
    echo "Usage: generate-commit-message.sh <issue_num> <issue_title> [epic_dir]"
    exit 1
fi

# Determine commit type from title
TYPE="fix"
if [[ "$ISSUE_TITLE" =~ ^Add|^Implement|^Create ]]; then
    TYPE="feat"
elif [[ "$ISSUE_TITLE" =~ ^Update|^Modify|^Change ]]; then
    TYPE="chore"
elif [[ "$ISSUE_TITLE" =~ ^Remove|^Delete ]]; then
    TYPE="refactor"
fi

# Build commit message
cat << COMMIT_MSG
$TYPE: $ISSUE_TITLE

Resolves #$ISSUE_NUM
COMMIT_MSG

# Add agent work summary if epic directory provided
if [[ -n "$EPIC_DIR" ]] && [[ -d "$EPIC_DIR/updates/$ISSUE_NUM" ]]; then
    echo ""
    for report in "$EPIC_DIR/updates/$ISSUE_NUM"/*.md; do
        if [[ -f "$report" ]]; then
            summary=$(grep -m 1 "^## Summary" "$report" -A 2 | tail -1 || echo "")
            if [[ -n "$summary" ]]; then
                echo "$summary"
            fi
        fi
    done
fi

# Add footer
cat << FOOTER

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
FOOTER
