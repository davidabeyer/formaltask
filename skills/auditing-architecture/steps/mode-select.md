---
consumes: [real-concern]
produces: [audit-mode]
---
# Phase 0: Mode Selection

**BLOCKING GATE:** Meta-analysis complete.

**quick:** Default to "Single module" scope. Skip AskUserQuestion unless target unclear.

**full:** Ask for scope:

```python
AskUserQuestion(questions=[{
    "question": "What scope for this architecture audit?",
    "header": "Mode",
    "options": [
        {"label": "Single module", "description": "Deep audit one module against quality criteria"},
        {"label": "Multi-module (Recommended)", "description": "Map architecture, then audit 2-4 modules sequentially"},
        {"label": "Full codebase", "description": "Architecture map + audit all major modules"}
    ],
    "multiSelect": False
}])
```

**Single module:** Skip to Phase 1-Single (no workers, direct audit).
**Multi-module / Full codebase:** Continue to Phase 1.
