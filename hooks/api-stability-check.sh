#!/bin/bash
# API Stability Check - Pre-commit hook
# Compares current API against baseline to detect breaking changes

set -e

BASELINE=".claude/api-baseline/hooks-lib.json"
CURRENT_DUMP="/tmp/hooks-lib-current.json"

# Skip if baseline doesn't exist
if [[ ! -f "$BASELINE" ]]; then
    echo "Warning: No API baseline found at $BASELINE"
    echo "   Run: PYTHONPATH=\"\$PWD\" griffe dump hooks.lib -d google -o $BASELINE"
    exit 0
fi

# Generate current API dump
PYTHONPATH="$PWD:$PYTHONPATH" griffe dump hooks.lib -d google -o "$CURRENT_DUMP" 2>/dev/null

if [[ ! -f "$CURRENT_DUMP" ]]; then
    echo "Warning: Could not generate current API dump"
    exit 0
fi

# Extract public function/class signatures from baseline
baseline_sigs=$(jq -r '.. | objects | select(.kind == "function" or .kind == "class") | select(.name | startswith("_") | not) | "\(.name):\(.kind)"' "$BASELINE" 2>/dev/null | sort -u)

# Extract from current
current_sigs=$(jq -r '.. | objects | select(.kind == "function" or .kind == "class") | select(.name | startswith("_") | not) | "\(.name):\(.kind)"' "$CURRENT_DUMP" 2>/dev/null | sort -u)

# Find removed public APIs (breaking changes)
removed=$(comm -23 <(echo "$baseline_sigs") <(echo "$current_sigs"))

if [[ -n "$removed" ]]; then
    echo ""
    echo "COMMIT BLOCKED: Breaking API changes detected"
    echo ""
    echo "Removed public APIs:"
    echo "$removed" | while read -r item; do
        echo "  - $item"
    done
    echo ""
    echo "To update baseline after intentional changes:"
    echo "   PYTHONPATH=\"\$PWD\" griffe dump hooks.lib -d google -o $BASELINE"
    rm -f "$CURRENT_DUMP"
    exit 1
fi

# Clean up
rm -f "$CURRENT_DUMP"

echo "API stability check passed"
exit 0
