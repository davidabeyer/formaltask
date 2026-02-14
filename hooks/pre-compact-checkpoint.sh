#!/usr/bin/env bash
#
# Pre-Compact Hook - Generate Handoff Context
#
# This hook generates handoff context files before compaction.
# Delegates to Python worker for actual processing.
#
# Worker: ~/.claude/hooks/pre-compact/pre_compact_worker.py
# Output: ~/.claude/tmp/handoff-{worktree}-{timestamp}.md
# Symlink: ~/.claude/tmp/handoff-{worktree}-latest.md

set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER="${HOOK_DIR}/pre-compact/pre_compact_worker.py"

if [[ ! -f "$WORKER" ]]; then
    echo "[PRE-COMPACT] ERROR: Worker not found: $WORKER" >&2
    exit 1
fi

# Pass stdin directly to worker and preserve exit code
exec python3 "$WORKER"
