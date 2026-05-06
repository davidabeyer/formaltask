#!/usr/bin/env bash
set -euo pipefail

export PATH="/Users/davidbeyer/.pyenv/shims:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

workspace_name="ft-watch"
workspace_command='cd /Users/davidbeyer/formaltask && exec ft work watch'

workspace_exists() {
  cmux list-workspaces | python3 -c 'import sys
name = sys.argv[1]
for line in sys.stdin:
    if line.strip().endswith(name):
        sys.exit(0)
sys.exit(1)' "$workspace_name"
}

for delay in 1 2 4 8 16; do
  if cmux ping >/dev/null 2>&1; then
    if workspace_exists; then
      exit 0
    fi
    cmux new-workspace --name "$workspace_name" --cwd /Users/davidbeyer/formaltask --command "$workspace_command" >/dev/null
    exit 0
  fi
  sleep "$delay"
done

cmux ping >/dev/null
if workspace_exists; then
  exit 0
fi
cmux new-workspace --name "$workspace_name" --cwd /Users/davidbeyer/formaltask --command "$workspace_command" >/dev/null
