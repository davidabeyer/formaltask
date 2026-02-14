---
consumes: [change-summary]
produces: [committed-branch]
---
# Phase 2: Commit Uncommitted Work

Invoke the `committing-changes` skill flow:

1. Read all diffs (staged + unstaged + untracked)
2. Propose logical commit groups (one logical change per commit)
3. Present groups with files, proposed messages, rationale
4. Gate: user approves groupings

```python
AskUserQuestion(questions=[{
    "question": "How do these commit groupings look?",
    "header": "Commits",
    "options": [
        {"label": "Looks good, commit all", "description": "Proceed with proposed groups"},
        {"label": "Squash into one commit", "description": "Single commit with everything"},
        {"label": "Revise groupings", "description": "I want different groupings"},
        {"label": "Abort", "description": "Don't commit, stop the workflow"}
    ],
    "multiSelect": false
}])
```

If "Abort": stop entirely.

Execute commits. Push branch: `git push -u origin {branch}`.
