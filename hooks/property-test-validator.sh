#!/bin/bash
# Property test validator for git pre-commit

# Get modified Python files
MODIFIED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' | grep -v '^tests/')

for FILE in $MODIFIED_PY_FILES; do
    MODULE=$(basename "$FILE" .py)
    PROPERTY_TEST="hooks/tests/property/test_${MODULE}_properties.py"

    if [[ -f "$PROPERTY_TEST" ]]; then
        pytest "$PROPERTY_TEST" -q > /dev/null 2>&1
        if [[ $? -ne 0 ]]; then
            echo "❌ COMMIT BLOCKED: Property tests failing"
            exit 1
        fi
    fi
done

exit 0
