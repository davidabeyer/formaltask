---
consumes: [scope]
produces: [goal]
---
## Phase 1: Capture Goal

**quick:** Use the description from $ARGUMENTS as the goal. Skip AskUserQuestion.

**full:**
```python
AskUserQuestion(questions=[{
    "question": "What's your goal in one sentence? (Your exact words, not Claude's interpretation)",
    "header": "Goal",
    "options": [{"label": "I'll type it", "description": "Capture exact intent"}],
    "multiSelect": False
}])
```

Store verbatim as `original_goal`. Goes in plan UNCHANGED — no Claude rewording.

**EXIT CRITERIA:** User's goal captured in their exact words.
