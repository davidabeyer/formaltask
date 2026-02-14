#!/bin/bash
# Check for uncommitted changes in working directory

set -euo pipefail

# Check git status
if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
    echo "❌ ERROR: uncommitted changes detected"
    echo ""
    echo "Please commit your work before proceeding:"
    echo ""
    git status --short
    exit 1
fi

# Clean working directory
exit 0
