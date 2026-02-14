#!/usr/bin/env bats

# Task #1798: Tests for better-hook.sh orchestrator removal
# Verifies that the deprecated orchestrator invocation has been removed

HOOK_FILE="$HOME/.tmux/plugins/tmux-claude-status/hooks/better-hook.sh"

@test "orchestrator module not invoked in hook" {
    # Assert hooks.lib.orchestrator invocation is removed
    run grep "hooks.lib.orchestrator" "$HOOK_FILE"

    # grep returns 1 when pattern NOT found (which is what we want)
    [[ "$status" -eq 1 ]]
}
