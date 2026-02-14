---
consumes: [scope-verdict]
produces: [epic-context]
---
# Phase 1: Validate Epic

**BLOCKING GATE:** None (first phase).

## Validate

```bash
ft epic list --names | grep -qx "$EPIC_NAME" || { echo "Epic '$EPIC_NAME' not found. Run: ft epic list"; exit 1; }
```

## No epic specified? Default to inbox with confirmation:

```python
AskUserQuestion(
    questions=[{
        "question": "Add this task to inbox epic?",
        "header": "Epic",
        "options": [
            {"label": "Yes, inbox", "description": "Default - quick capture, triage later"},
            {"label": "No, different epic", "description": "I'll specify which epic"}
        ],
        "multiSelect": False
    }]
)
```

If user selects "No, different epic", ask them to name the epic.

## Exit Criteria

Epic name validated against `ft epic list --names` output.
