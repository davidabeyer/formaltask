---
consumes: [target-file]
produces: [code-index]
optional: true
---
## Phase 4: Exhaustive Reading (full only)

**quick:** Read file yourself. Note style observations inline. Skip subagent.

**full:** Single opus agent reads EVERY line. Produces code index with actual code blocks.

```python
Task(
    subagent_type="general-purpose",
    model="opus",
    description=f"Exhaust-read {target}",
    prompt=f"""Read {target} exhaustively. For EVERY function:
- Quote the actual code (not summaries)
- Note initial style observations with line numbers
Write to: outputs/01-code-index.md"""
)
```

**QUALITY GATE:** Code index must have actual code blocks, not "handles X".

**EXIT CRITERIA:** `01-code-index.md` exists with real code
