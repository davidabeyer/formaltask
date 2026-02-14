#!/bin/bash
# SessionStart hook: Warn if local master is behind remote.
# Skips in worktrees (detected by .task/id file).

test -f .task/id && exit 0

branch=$(git branch --show-current 2>/dev/null)
test "$branch" = master || exit 0

git fetch origin master -q 2>/dev/null || exit 0

behind=$(git rev-list --count master..origin/master 2>/dev/null)
test "${behind:-0}" -gt 0 && echo "⚠️ Local master is $behind commits behind. Run: git pull"

exit 0
