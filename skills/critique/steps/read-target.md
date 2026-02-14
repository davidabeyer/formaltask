---
consumes: [target-type, target-paths]
produces: [target-content, claims]
---

# Phase 1: Read Target

**quick:** Read target directly, extract key claims. No subagent.

**full:** Read all related files (plan + discovery, or all specs).

**For TASK:** Read task.md, extract title, epic, criteria, files to modify.

**For PLAN/SPECS:** Read plan file OR all specs. Extract claims to verify.

**EXIT CRITERIA:** Target content loaded, claims extracted for verification.
