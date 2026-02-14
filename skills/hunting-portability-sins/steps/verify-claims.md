---
consumes: [cross-cutting-analysis]
produces: [verified-findings]
optional: true
---

# Verify Claims

**quick:** Verify top findings inline. No formal verification step.

**full:** **BLOCKING GATE:** Cross-cutting analysis complete.

```python
Skill("verifying-claims")  # spot-check hardcoded paths, env var defaults, tool deps
```

Focus:
- Claimed hardcoded paths actually exist in code
- Env vars actually lack defaults
- Tool dependencies are real

**Auditors hypothesize. Verification confirms.** False positives waste migration effort.

## Exit Criteria

P0 blockers verified or findings corrected.
