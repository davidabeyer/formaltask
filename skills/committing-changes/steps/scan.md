---
consumes: []
produces: [change-inventory]
---

## Phase 1: Scan Changes

**BLOCKING GATE:** Must be in a git repository.

Run these in parallel:

```bash
git status          # untracked + modified + staged
git diff            # unstaged changes (content)
git diff --cached   # staged changes (content)
git log --oneline -10  # recent local commits for context
```

Read every changed file. Understand what each change DOES, not just what file it touches.

**EXIT CRITERIA:** Full picture of all uncommitted/untracked work.
