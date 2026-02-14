---
consumes: [chosen-approach, requirements]
produces: [implementation-plan]
---

## Phase 5: Plan

**BLOCKING GATE:** Approach selected.

**quick:** Create plan directly. Skip checkpoint XML.

**full:** Before creating plan, verify approach matches original need:

```xml
<checkpoint>
  <verify>Does chosen approach address the REAL DECISION from meta-analysis? [YES/NO]</verify>
  <verify>Did user choose based on complete information (no hidden cons)? [YES/NO]</verify>
  <verify>Plan tasks are specific enough to execute without questions? [YES/NO]</verify>
  <conclusion>
    APPROACH: [chosen]
    ADDRESSES: [what problem it solves]
    TRADES_OFF: [what they're giving up]
  </conclusion>
  <flips_if>[What would make them regret this choice—e.g., "if traffic grows 10x before v2"]</flips_if>
</checkpoint>
```

Create plan with:
- file:line references
- Task breakdown (30min-2hr each)
- Dependency ordering
- Acceptance criteria

```python
run.write_synthesis(final_comparison)
run.publish_report()
```
