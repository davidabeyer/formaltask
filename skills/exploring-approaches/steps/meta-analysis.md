---
consumes: [user-request]
produces: [real-decision, constraints]
---

## Phase -1: Meta-Analysis

**BLOCKING GATE:** User request received.

**quick:** Note the real decision and constraints in one sentence. Skip XML.

**full:** Before exploring approaches, understand the decision space:

```xml
<meta_analysis>
  <stated_request>[What they asked—"how should I implement X", "plan this feature"]</stated_request>
  <real_decision>[What's the actual fork in the road? "Build vs buy"? "Now vs later"? "Speed vs quality"?]</real_decision>
  <decision_already_made>[Are they ACTUALLY exploring, or validating a choice they've already made?]</decision_already_made>
  <constraints_hidden>[Deadlines, team skills, politics—what will kill "correct" approaches?]</constraints_hidden>
  <explorer_bias>[Am I going to build a straw man for Simple so Balanced wins? Check honest advocacy.]</explorer_bias>
</meta_analysis>
```

**EXIT CRITERIA:** Understand the real decision before spawning explorers.
