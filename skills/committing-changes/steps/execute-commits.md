---
consumes: [approved-groupings]
produces: [commits-done]
---

## Phase 3: Execute Commits

For each approved group, in order:

1. `git add` the specific files for that group
2. `git commit -m "{approved message}"`
3. Confirm success before moving to next group

If a single file has changes belonging to different groups: `git add -p` is interactive and won't work in automated Bash. Instead, use `git diff {file}` to show hunks, create a temporary copy, Edit the file to contain only the changes for this group, `git add {file}`, commit, then restore the full version for the next group.

If a commit fails (hook rejection, etc.): stop, show the error, ask how to proceed.

**EXIT CRITERIA:** All approved groups committed.
