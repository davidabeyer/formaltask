---
consumes: [user-request]
produces: [real-concern]
---
# Phase -1: Meta-Analysis

**BLOCKING GATE:** Audit request received.

**quick:** Note the real concern in one sentence. Skip XML.

**full:** Before selecting audit mode, understand what's really being asked:

```xml
<meta_analysis>
  <stated_request>[What they asked—"audit the codebase", "check architecture", "review module X"]</stated_request>
  <real_concern>[What's driving this? Performance problems? Security worry? "Code feels messy"? Onboarding friction?]</real_concern>
  <hidden_question>[Is this actually "help me understand" disguised as "audit"? "Validate my concerns" vs "find problems"?]</hidden_question>
  <audit_scope>[Are they worried about ONE thing across all modules, or EVERYTHING about one module?]</audit_scope>
  <anti_pattern_risk>[Am I about to audit for MY preferences instead of THEIR problems?]</anti_pattern_risk>
</meta_analysis>
```

**EXIT CRITERIA:** Understand the real concern before choosing audit mode.
