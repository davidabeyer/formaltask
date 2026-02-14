---
consumes: [pull-request]
produces: [merged-result]
---
# Phase 4: Merge and Cleanup

Present merge plan:

```markdown
### Ready to merge and cleanup

- **Merge:** squash-merge PR #{number} into {main}
- **Delete:** remote branch `{branch}`
- **Delete:** local worktree at `{worktree-path}`
- **Delete:** local branch `{branch}`
```

Gate:

```python
AskUserQuestion(questions=[{
    "question": "Merge PR and delete worktree?",
    "header": "Merge",
    "options": [
        {"label": "Merge + cleanup (Recommended)", "description": "Squash merge, delete worktree and branch"},
        {"label": "Merge only", "description": "Merge PR but keep worktree"},
        {"label": "Copy cleanup to clipboard", "description": "Copy merge+delete commands to clipboard, I'll run manually"},
        {"label": "Stop here", "description": "PR created, I'll merge later"}
    ],
    "multiSelect": false
}])
```

If "Stop here": show the PR URL and stop.

If "Copy cleanup to clipboard":

```bash
# Build cleanup commands
CLEANUP_CMD="# Merge and cleanup for PR #{number}
gh pr merge {number} --squash --delete-branch --admin
cd {main-worktree-path}
git worktree remove {worktree-path}
git branch -D {branch}"

# Copy to clipboard (macOS)
echo "$CLEANUP_CMD" | pbcopy
```

Show user:
```markdown
**Copied to clipboard:**
\`\`\`bash
# Merge and cleanup for PR #{number}
gh pr merge {number} --squash --delete-branch --admin
cd {main-worktree-path}
git worktree remove {worktree-path}
git branch -D {branch}
\`\`\`

PR: {pr-url}
Paste and run when ready to merge.
```

Stop.

If merge requested:

```bash
# Check CI status first
gh pr checks {number}
```

If checks are pending: `gh pr checks {number} --watch --fail-fast --interval 30`
If checks fail: show failure, stop. User fixes and re-invokes.

```bash
# Merge
gh pr merge {number} --squash --delete-branch

# Return to main repo before removing worktree
cd {main-worktree-path}

# Cleanup worktree
git worktree remove {worktree-path}

# Delete local branch (remote branch deleted by --delete-branch)
git branch -D {branch} 2>/dev/null

# Verify clean
git worktree list
```

If merge fails (conflicts, checks): show error, suggest next steps.
