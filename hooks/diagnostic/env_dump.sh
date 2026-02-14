#!/bin/bash
# Diagnostic hook - dumps environment to file for debugging
# Add this to settings.json as PreToolUse hook to see what environment hooks get

DUMP_FILE="/tmp/claude-hook-env-dump-$(date +%s).txt"

{
    echo "=== Claude Code Hook Environment Dump ==="
    echo "Timestamp: $(date)"
    echo "PWD: $PWD"
    echo ""
    echo "=== PATH ==="
    echo "$PATH" | tr ':' '\n'
    echo ""
    echo "=== SHELL ==="
    echo "SHELL: $SHELL"
    echo "\$0: $0"
    echo ""
    echo "=== Key Env Vars ==="
    echo "HOME: $HOME"
    echo "USER: $USER"
    echo "CLAUDE_PROJECT_DIR: $CLAUDE_PROJECT_DIR"
    echo "CLAUDE_ENV_FILE: $CLAUDE_ENV_FILE"
    echo ""
    echo "=== Full Environment ==="
    env | sort
    echo ""
    echo "=== Which commands available ==="
    echo "python3: $(which python3 2>&1)"
    echo "python: $(which python 2>&1)"
    echo "bash: $(which bash 2>&1)"
    echo "env: $(which env 2>&1)"
} > "$DUMP_FILE" 2>&1

echo "Environment dumped to: $DUMP_FILE" >&2
exit 0
