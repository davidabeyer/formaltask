---
consumes: [lens-outputs]
produces: [verified-findings]
optional: true
---

## Verify Against Exemplars (full only)

**quick:** Skip. No lens outputs to verify.

**full:** Challenge every finding against real-world exemplars.

```python
Task(
    subagent_type="general-purpose",
    prompt=f"""Read all lens outputs.

For each finding:
1. Check how requests/click/pydantic handle this
2. If they do same thing, REJECT the finding
3. Only CONFIRM genuine deviations from excellence

Write to: outputs/verified.md"""
)

# Verify against codebase reality
Skill("verifying-claims")  # spot-check "missing docstring", "no validation", "security vuln" claims
```

**EXIT CRITERIA:** Verified findings documented. False positives rejected.
