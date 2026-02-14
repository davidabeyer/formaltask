---
consumes: [target-file]
produces: [style-mode]
---
## Phase 0: Mode Selection

**quick:** Default to single file mode. Skip AskUserQuestion.

**full:**
```python
AskUserQuestion(questions=[{
    "question": "What scope for this style audit?",
    "header": "Mode",
    "options": [
        {"label": "Single file", "description": "Deep 6-pass audit of one file"},
        {"label": "Single module (Recommended)", "description": "Audit all files in one directory"},
        {"label": "Multiple modules", "description": "Parallel workers across directories"}
    ],
    "multiSelect": False
}])
```

**Single file / Single module:** Continue to Phase 1.
**Multiple modules:** Read `skills/_references/orchestration.md`, spawn workers per module, synthesize cross-module patterns.
