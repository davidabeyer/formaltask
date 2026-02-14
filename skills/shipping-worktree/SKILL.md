---
name: shipping-worktree
description: >-
  Ships a worktree: reviews changes, commits in logical groups, creates PR,
  merges, cleans up worktree+branch. Use when "ship worktree", "land worktree",
  "ship-worktree", or finishing work in a git worktree. For commits only,
  use committing-changes instead.
invoke_with:
- /ship-worktree
allowed-tools: Bash(git *), Read, Write, Edit, Grep, Glob
---

## Current State
!`git status 2>/dev/null`
!`git diff --stat 2>/dev/null`
!`git log --oneline -5 2>/dev/null`

<role>
WHO: Worktree landing controller
ATTITUDE: Ship clean or don't ship. No orphaned worktrees.
</role>

<purpose>
Your job is to land a worktree's work — from dirty working tree to merged PR to deleted worktree — with user confirmation at every gate.
</purpose>

<workflow>

## Phase 0: Detect Worktree
Read and follow `steps/detect-worktree.md`.

## Phase 1: Review Changes
Read and follow `steps/review-changes.md`.

## Phase 2: Commit Uncommitted Work
Read and follow `steps/commit.md`.

## Phase 3: Create PR
Read and follow `steps/create-pr.md`.

## Phase 4: Merge and Cleanup
Read and follow `steps/merge-cleanup.md`.

---

## Checkpoint

```xml
<checkpoint>
  <verify>Worktree detected and validated? [YES/NO]</verify>
  <verify>All changes committed with user approval? [YES/NO]</verify>
  <verify>PR created with user-approved title/body? [YES/NO]</verify>
  <verify>Merge + cleanup completed? [YES/NO]</verify>
  <conclusion>{PR URL} merged. Worktree {path} removed.</conclusion>
</checkpoint>
```

</workflow>

<rules>
- Never commit, create PR, merge, or delete without explicit user confirmation.
- Never force-push. Never force-delete without showing what's being deleted.
- If CWD is not a worktree, stop immediately. Don't guess paths.
- Squash merge is default. Clean history on main.
- cd back to main repo BEFORE removing the worktree — otherwise the shell breaks.
- If merge conflicts: show the error, don't attempt auto-resolution. User decides.
- Commit messages use conventional commits (feat:, fix:, refactor:, etc.).
- PR title matches the primary commit or summarizes the branch's work.
</rules>
