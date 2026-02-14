---
consumes: [worktree-context]
produces: [change-summary]
---
# Phase 1: Review Changes

Run in parallel:

```bash
git status --short                          # all changes
git diff --stat                             # unstaged summary
git diff --cached --stat                    # staged summary
git log --oneline $(git merge-base HEAD master)..HEAD  # commits since fork
```

Present a summary:

```markdown
### Worktree: {path}
**Branch:** {branch} (forked from {main} at {merge-base-short})
**Commits since fork:** {N}
**Uncommitted changes:** {staged} staged, {unstaged} modified, {untracked} untracked
```

If NO uncommitted changes AND commits exist: skip to Phase 3 (create-pr).
If NO uncommitted changes AND NO commits: tell user there's nothing to ship. Stop.
