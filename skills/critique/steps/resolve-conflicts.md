---
consumes: [auditor-findings]
produces: [verified-findings]
optional: true
---

# Phase 4: Resolve Auditor Conflicts (full only)

**quick:** Skip this phase. No auditors to reconcile.

**full:** **Auditors contradict each other and can be factually wrong about tool semantics (e.g., exit codes, grep behavior). Verify before trusting.**

For each P0/P1 where auditors disagree or make quantitative/behavioral claims:
1. Run the actual command against the codebase
2. Record: claim → actual result → VALID/INVALID/MISLEADING
3. **De-dupe overlaps:** When multiple auditors flag the same AC/section, merge into one finding using the most complete fix. Drop the weaker duplicate.

Downgrade findings whose evidence is wrong but whose fix is still correct (e.g., wrong explanation, right remedy → P1 not P0).

**EXIT CRITERIA:** All contested claims verified with tool evidence. Overlaps merged into single findings.
