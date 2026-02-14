---
consumes: [verified-findings, real-concern]
produces: [audit-report]
optional: true
---
# Phase 5: Synthesis (full only)

**quick:** Skip this phase. Write findings directly in Phase 1-Single.

**full:** Before compiling report, verify synthesis addresses the real need:

```xml
<checkpoint>
  <verify>Does this report answer the REAL CONCERN from meta-analysis? [YES/NO]</verify>
  <verify>Every finding is CONFIRMED (not just asserted)? [YES/NO]</verify>
  <verify>Rejected findings are documented (transparency)? [YES/NO]</verify>
  <verify>Recommendations are prioritized by USER value, not MY preference? [YES/NO]</verify>
  <conclusion>
    FINDING_COUNT: [N confirmed]
    TOP_PRIORITY: [Most important finding for THIS user]
    AUDIT_VERDICT: [Healthy | Needs Work | Significant Issues]
  </conclusion>
  <flips_if>[What context would change these findings—e.g., "if the complexity is intentional for performance"]</flips_if>
</checkpoint>
```

Compile verified findings into report:

- Executive summary
- Understanding summary
- Verified findings (grouped by severity)
- Rejected findings (transparency)
- Prioritized recommendations

Write to `synthesis.md`. See [output-template.md](references/output-template.md).
