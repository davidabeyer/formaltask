---
consumes: [target-file, code-index]
produces: [pass-findings]
---
## Phase 5: Sequential Passes (full only)

**quick:** Skip 6 sequential passes. Audit naming, typing, pythonic patterns yourself inline. Present findings directly.

**full:** Run 6 passes sequentially. Each builds on previous.

| Pass | Question | Looks For |
|------|----------|-----------|
| **Naming** | Self-documenting? | Single letters, abbrevs, inconsistency |
| **Typing** | Complete and correct? | Missing hints, `Any`, wrong types |
| **Pythonic** | Would senior Pythonista write this? | `range(len())`, non-idiomatic |
| **Organization** | Clean structure? | Import order, `__all__`, boundaries |
| **Documentation** | Understandable? | Missing docstrings, stale comments |
| **Modernization** | Current Python? | `os.path` vs pathlib, `%` vs f-string |

For each pass:
```python
Task(
    subagent_type="general-purpose",
    model="opus",
    description=f"Pass: {pass_name}",
    prompt=f"""Read 01-code-index.md and previous pass outputs.
Focus: {pass_name}
Output findings with file:line citations to: outputs/02-pass-{pass_name}.md"""
)
# WAIT for completion before next pass
```

**Why sequential:** Naming informs typing. Typing reveals patterns. Context accumulates.

**EXIT CRITERIA:** All 6 pass outputs exist
