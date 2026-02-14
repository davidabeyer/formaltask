---
consumes: [change-inventory]
produces: [approved-groupings]
---

## Phase 2: Propose Groupings

Analyze changes and group them by **logical unit of work** — not by file type or directory.

Good groupings:
- One feature or fix per commit
- Related test + implementation together
- Config changes that enable a feature, with that feature
- Unrelated formatting/cleanup as its own commit

Bad groupings:
- "All Python files" / "All tests"
- Mixing unrelated fixes
- Separating a feature from its tests

Present each proposed group:

```markdown
### Commit Group {N}: {title}

**Files:**
- path/to/file.py (what changed)
- path/to/test.py (what changed)

**Proposed message:** {conventional commit message}

**Rationale:** {why these belong together}
```

Then ask:

```python
AskUserQuestion(questions=[{
    "question": "How do these commit groupings look?",
    "header": "Groupings",
    "options": [
        {"label": "Looks good, commit all", "description": "Proceed with all groups as proposed"},
        {"label": "Revise groupings", "description": "I want to change how things are grouped"},
        {"label": "Edit messages", "description": "Groupings are fine but I want different commit messages"},
        {"label": "Skip some groups", "description": "Only commit some of these groups"}
    ],
    "multiSelect": False
}])
```

If "Revise groupings": Ask what to change, re-propose, re-confirm. Loop until approved.

**EXIT CRITERIA:** User approved all commit groups.
