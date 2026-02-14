---
consumes: [requirements, codebase-context]
produces: [approach-analyses]
fan_out: [simple, scalable, balanced]
optional: true
---

## Phase 3: Spawn Explorers (full only)

**quick:** Skip subagents. Present 2-3 approaches yourself inline with pros/cons.

**full:** Spawn ALL 3 in SINGLE message — pass context directly in prompts:

```python
for persona, question in [("simple", "FASTEST"), ("scalable", "ROBUST"), ("balanced", "PRAGMATIC")]:
    Task(subagent_type="general-purpose", description=f"{persona.title()} Explorer",
         run_in_background=True,
         prompt=f"""# {persona.title()} Explorer

## Mission
Find the {question} path for: {feature_description}

## Context
Read: {run.context}

## Your Question
What's the {question} path?

## Output
Write JSON to: {run.outputs}/{persona}-explorer.json
""")
```

**EXIT CRITERIA:** All 3 explorers complete.
