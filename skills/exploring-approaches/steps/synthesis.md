---
consumes: [approach-analyses, real-decision]
produces: [comparison, chosen-approach]
---

## Phase 4: Synthesis

**BLOCKING GATE:** All outputs received (full) or approaches presented (quick).

**quick:** Present comparison table inline. Skip adversarial XML. Wait for user choice.

**full:** Read outputs and verify approaches:

```python
outputs = run.read_all_outputs()
simple = json.loads(outputs["simple-explorer"])
scalable = json.loads(outputs["scalable-explorer"])
balanced = json.loads(outputs["balanced-explorer"])
```

Before presenting, verify approaches are genuinely different:

```xml
<adversarial>
  <future_state>User picked Balanced. 3 months later, they're frustrated.</future_state>
  <straw_man_check>[Was Simple a genuine FASTEST path, or did I sabotage it to make Balanced win?]</straw_man_check>
  <scalable_overkill>[Was Scalable genuinely robust, or did I add complexity to make it scary?]</scalable_overkill>
  <hidden_winner>[Did the explorers actually explore, or did I pre-decide the "right" answer?]</hidden_winner>
  <missing_approach>[Is there a 4th approach none of the explorers considered?]</missing_approach>
</adversarial>
```

Build comparison:

| Aspect | Simple | Balanced | Scalable |
|--------|--------|----------|----------|
| Files Changed | X | Y | Z |
| Effort | low | medium | high |
| Tech Debt | significant | minor | none |

Present pros/cons. **Wait for user choice.**

**EXIT CRITERIA:** User chooses approach.
