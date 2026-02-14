---
consumes: [committed-branch]
produces: [pull-request]
---
# Phase 3: Create PR

Build PR from the full commit history on this branch:

```bash
git log --oneline $(git merge-base HEAD master)..HEAD  # all commits
git diff $(git merge-base HEAD master)..HEAD --stat     # total diff
```

Draft and present the PR:

```markdown
### Proposed PR

**Title:** {conventional-commit-style title}

**Body:**
## Summary
{2-4 bullets summarizing the changes}

## Test plan
{checklist of verification steps}
```

Gate:

```python
AskUserQuestion(questions=[{
    "question": "Create this PR?",
    "header": "PR",
    "options": [
        {"label": "Create PR", "description": "Create as shown"},
        {"label": "Edit title/body", "description": "I want to change something"},
        {"label": "Abort", "description": "Don't create PR, stop here"}
    ],
    "multiSelect": false
}])
```

If "Edit": ask what to change, revise, re-confirm.
If "Abort": stop.

Create:
```bash
gh pr create --title "{title}" --body "{body}" --base {main-branch}
```
