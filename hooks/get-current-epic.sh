#!/bin/bash
# Auto-detect current epic from git branch

# Get current branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# If on epic/* branch, extract epic name
if [[ "$BRANCH" =~ ^epic/(.+)$ ]]; then
    echo "${BASH_REMATCH[1]}"
    exit 0
fi

# If not in epic branch, check for .epic-context file (fallback)
if [[ -f ".epic-context" ]]; then
    EPIC_NAME=$(cat ".epic-context" | tr -d '[:space:]')
    if [[ -n "$EPIC_NAME" ]]; then
        echo "$EPIC_NAME"
        exit 0
    fi
fi

# No epic context detected
echo "none"
exit 1
