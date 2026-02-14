#!/usr/bin/env bash
# pm-dashboard.sh - Launcher script for FormalTask dashboard
# Task #1776: CLI entry point for dashboard session management
set -euo pipefail

SESSION_NAME="${PM_DASHBOARD_SESSION:-pm-dashboard}"

# Validate required tools
if ! command -v tmux &>/dev/null; then
    echo "Error: tmux is required but not installed" >&2
    exit 1
fi
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not installed" >&2
    exit 1
fi

# Show usage
show_usage() {
    cat << 'USAGE'
Usage: pmd [OPTIONS] [PATH]

Launch or manage the FormalTask dashboard.

Options:
  -h, --help    Show this help message
  -k            Kill the dashboard session

Arguments:
  PATH          Optional project directory (default: current directory)
USAGE
}

# Handle help flags
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    show_usage
    exit 0
fi

# Handle -k (kill) flag
if [[ "${1:-}" == "-k" ]]; then
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        tmux kill-session -t "$SESSION_NAME"
        echo "Dashboard session killed"
    else
        echo "Dashboard not running"
    fi
    exit 0
fi

# Handle optional path argument
PROJECT_ROOT="${1:-$(pwd)}"
if [[ ! -d "$PROJECT_ROOT" ]]; then
    echo "Error: Directory not found: $PROJECT_ROOT" >&2
    exit 1
fi

# Check if dashboard session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    # Session exists - switch or attach based on context
    if [[ -n "${TMUX:-}" ]]; then
        # Inside tmux - use switch-client
        tmux switch-client -t "$SESSION_NAME"
    else
        # Outside tmux - use attach-session
        tmux attach-session -t "$SESSION_NAME"
    fi
else
    # Session doesn't exist - create new session with dashboard
    if [[ -n "${TMUX:-}" ]]; then
        # Inside tmux - create detached and switch
        tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_ROOT" \
            "python3 -m formaltask.cli.pm dashboard"
        tmux switch-client -t "$SESSION_NAME"
    else
        # Outside tmux - create and attach
        tmux new-session -s "$SESSION_NAME" -c "$PROJECT_ROOT" \
            "python3 -m formaltask.cli.pm dashboard"
    fi
fi
