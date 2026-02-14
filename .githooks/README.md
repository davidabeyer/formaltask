# Git Hooks

Version-controlled git hooks for the claude-code project.

## Setup (Required for New Clones)

After cloning, configure git to use these hooks:

```bash
git config core.hooksPath .githooks
```

This is automatically inherited by git worktrees.

## Hooks

| Hook | Purpose |
|------|---------|
| `commit-msg` | Validates commit message format |
| `pre-commit` | Runs linting, security checks, TDD guard |
| `pre-merge-commit` | Blocks merges when task not completed |
| `pre-push` | Validates task status before push (blocks `task-{id}` branches if not completed) |

## Task Status Enforcement

The `pre-push` hook enforces FormalTask workflow:

- Branches matching `task-{id}` pattern are checked against the database
- Push is blocked unless task status is: `completed`, `pending_merge`, `pending_review`, or `closed`
- Bypass with `git push --no-verify` (use sparingly)

## Feature Branch Isolation

The `pre-push` hook also enforces feature branch isolation:

- When an epic has `feature_branch` set, task branches cannot push directly to master
- The hook tells you which feature branch to target instead
- Use `gh pr create --base feature/epic-name` to create PRs to the feature branch
- Set feature branch via: `ft epic-update <epic> --feature-branch <branch>`

## User-Specific Hooks

User-specific hooks (like `post-commit` for auto-docs) should be configured separately:

```bash
# Example: Add post-commit hook
ln -sf ~/.claude/hooks/post-commit-auto-docs.sh .git/hooks/post-commit
```

Note: `.git/hooks/` still works for user-specific hooks that shouldn't be shared.
