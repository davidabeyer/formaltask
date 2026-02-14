---
consumes: [commits-done]
produces: [sync-result]
---

## Phase 4: Sync Decision

```python
AskUserQuestion(questions=[{
    "question": "Want to sync with remote?",
    "header": "Sync",
    "options": [
        {"label": "Pull and push", "description": "Fetch latest, rebase, then push"},
        {"label": "Pull only", "description": "Fetch and integrate remote changes"},
        {"label": "Push only", "description": "Push local commits to remote"},
        {"label": "Skip sync", "description": "Done for now, no remote operations"}
    ],
    "multiSelect": False
}])
```

If "Skip sync": Done. End workflow.

If pulling: `git pull --rebase` (prefer rebase for clean history). If that fails or conflicts arise, proceed to conflict-resolution step.

If pushing after successful pull: `git push`. Confirm success.

**EXIT CRITERIA:** Sync complete or skipped.
