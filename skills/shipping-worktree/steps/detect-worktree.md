---
consumes: [user-request]
produces: [worktree-context]
---
# Phase 0: Detect Worktree

**BLOCKING GATE:** Must be inside a git worktree (not the main repo).

```bash
git rev-parse --show-toplevel        # current repo root
git worktree list                    # all worktrees
git symbolic-ref --short HEAD        # current branch
git rev-parse --abbrev-ref @{u} 2>/dev/null  # upstream tracking
```

Verify:
- CWD is a worktree (not the main working tree)
- Identify: worktree path, branch name, main branch (master/main)

If NOT a worktree: tell the user and stop. Suggest `cd` to the worktree first.

If args provided (e.g., `/ship-worktree task-2659`): resolve path from `git worktree list` and `cd` there.
