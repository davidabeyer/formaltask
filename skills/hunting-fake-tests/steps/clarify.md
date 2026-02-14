---
consumes: []
produces: [audit-scope]
---

**quick:** Skip AskUserQuestion. Default to full suite scope, hunt all anti-patterns.

**full:**
```python
AskUserQuestion(
    questions=[
        {
            "question": "What test scope to audit?",
            "header": "Scope",
            "options": [
                {"label": "Full suite", "description": "All tests in codebase"},
                {"label": "Specific path", "description": "Tests in a directory"},
                {"label": "Critical paths", "description": "Tests for critical functionality"}
            ],
            "multiSelect": False
        },
        {
            "question": "Quality concerns?",
            "header": "Focus",
            "options": [
                {"label": "Fake tests", "description": "No assertions, trivial checks"},
                {"label": "Weak assertions", "description": "Never fail meaningfully"},
                {"label": "Over-engineered", "description": "Antirez violations"},
                {"label": "Isolation failures", "description": "Shared state, order deps"}
            ],
            "multiSelect": True
        }
    ]
)
```

**EXIT CRITERIA:** Have scope and focus areas
