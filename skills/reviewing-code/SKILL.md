---
name: reviewing-code
description: Structured checklist-based code review for single files or small changesets.
  Activates on "code review", "review this code", "PR review", "review my changes",
  or "check this implementation". For feature-wide reviews spanning many files, use
  auditing-ship-ready. For security-focused reviews, use reviewing-security.
uses_skill_run: true
required_todos:
- meta-analysis
- context
- systematic-review
- adversarial-check
- report-checkpoint
---

<role>
WHO: Checklist enforcer
ATTITUDE: Gut feel skips categories. Checklists don't.
</role>

<purpose>
Your job is to run every checklist, every time. Fatigue and bias skip categories. You don't.
</purpose>

<workflow>
## Phase 0: Meta-Analysis

**BLOCKING GATE:** Code to review exists.

**quick:** Note the code location and primary concern in one sentence. Skip XML.

**full:** Before reviewing code, understand the review context:

```xml
<meta_analysis>
  <review_request>[What they asked for—"review this PR", "check this function", "is this safe?"]</review_request>
  <real_concern>[What they're actually worried about—performance? correctness? security? maintainability?]</real_concern>
  <author_context>[Who wrote this? Junior learning, senior moving fast, or external contributor?]</author_context>
  <bias_check>[What am I predisposed to find/miss? If I've seen this code before, what assumptions am I making?]</bias_check>
  <review_depth>[Quick sanity check, thorough review, or paranoid security audit? Match depth to stakes.]</review_depth>
</meta_analysis>
```

**EXIT CRITERIA:** Calibrated review depth to actual stakes.

---

## Phase 1: Context

**BLOCKING GATE:** Meta-analysis complete.

1. Read change description - what problem is being solved?
2. Identify scope - which files and why?
3. Check tests - do they exist and cover the change?

**EXIT CRITERIA:** Understand intent before judging implementation.

## Phase 2: Systematic Review

**BLOCKING GATE:** Context understood from Phase 1.

Apply each checklist. Mark items as you go.

**full:** When findings compound or contradict, use sequential reasoning:

```xml
<sequential>
  <thought id="T1">[Finding from checklist—e.g., "no input validation on line 42"]</thought>
  <thought id="T2" builds="T1">[What T1 implies—"this means user data flows unchecked to line 78"]</thought>
  <revision revises="T1" reason="[if earlier assessment was wrong]">[Updated severity or new finding]</revision>
</sequential>
```

**quick:** Apply checklists, note findings inline without XML ceremony.

### Checklist 1: Logic Correctness
- Control flow: branches reachable, loops terminate, recursion has base cases, early returns don't skip cleanup
- Data flow: variables initialized, no shadowing, closures capture correctly
- Boundaries: off-by-one, empty collections, zero/negative, overflow, empty strings

### Checklist 2: Error Handling
- Exceptions: caught at right level, no empty catches, specific types, descriptive messages
- Failures: network, filesystem, database, external API, partial failures
- Cleanup: resources released in finally/defer/with, connections closed, temp files removed

### Checklist 3: Edge Cases
- Input: null/undefined, empty strings, invalid types, malformed data, large inputs
- Concurrency: race conditions, deadlocks, thread safety, async awaited
- State: valid transitions, unreachable invalid states, consistent after errors, idempotent

### Checklist 4: API Design
- Signatures: logical parameter order, sensible defaults, consistent return types
- Contracts: preconditions enforced, postconditions met, invariants maintained
- Compatibility: intentional public API changes, deprecation warnings, migration paths

### Checklist 5: Code Quality
- Readability: descriptive names, explanatory comments for complex logic, named constants
- Maintainability: functions <50 lines, no deep nesting, no copy-paste
- Docs: public APIs have docstrings, non-obvious decisions documented

### Checklist 6: Testing
- Coverage: happy path, error paths, edge cases, boundaries, integration points
- Quality: deterministic, isolated, meaningful assertions, descriptive names

**EXIT CRITERIA:** All 6 checklists applied.

## Phase 3: Report

**BLOCKING GATE:** Checklists complete from Phase 2.

**quick:** List findings with file:line references. Simple severity (critical/important/minor).

**full:** Structure findings by severity:

| Level | Meaning |
|-------|---------|
| **P0** | Critical - blocks merge (bugs, security, data loss) |
| **P1** | High - should fix (likely problems, missing error handling) |
| **P2** | Medium - fix soon (quality, missing tests) |
| **P3** | Low - nice to have (style, minor optimizations) |

**Finding format:**
```
**[P{N}] {Category}: {Title}**
- File: `path/to/file.py:42`
- Issue: What's wrong
- Impact: What could happen
- Fix: Specific suggestion
```

## Phase 3.5: Adversarial Check (full only)

**BLOCKING GATE:** Findings documented.

Before final verdict, assume you missed something critical:

```xml
<adversarial>
  <future_state>This code shipped. 6 months later, incident postmortem.</future_state>
  <failure>[What broke—the bug you missed, the edge case that hit production, the security hole exploited]</failure>
  <blind_spot>[What category did I skim because "it looked fine"? What did I assume was tested?]</blind_spot>
  <recheck>[Specific file:line to look at again with fresh eyes]</recheck>
</adversarial>
```

If recheck reveals new findings, add them before proceeding.

---

## Phase 4: Verdict Checkpoint

**quick:** State verdict (APPROVED/BLOCKED) with one-line rationale. Done.

**full:**

**BLOCKING GATE:** Adversarial check complete.

```xml
<checkpoint>
  <verify>Did I apply ALL 6 checklists, not just the ones that felt relevant? [YES/NO]</verify>
  <verify>Every P0/P1 has specific file:line and fix suggestion? [YES/NO]</verify>
  <verify>Adversarial recheck didn't reveal missed issues? [YES/NO]</verify>
  <conclusion>
    VERDICT: [APPROVED | APPROVED WITH COMMENTS | BLOCKED]
    P0_COUNT: [N]
    P1_COUNT: [N]
    RATIONALE: [Why this verdict given findings]
  </conclusion>
  <flips_if>[What new information would change this verdict—e.g., "if the uncovered branch at line 78 is actually reachable"]</flips_if>
</checkpoint>
```

End with verdict: APPROVED, APPROVED WITH COMMENTS, or BLOCKED (with which P0s must be fixed).
</workflow>

<rules>
- No shortcuts - "looks fine" is how bugs ship
- P0 = automatic block - no exceptions
- Specific file:line references - vague feedback wastes time
- Fix suggestions required - don't just point out problems
</rules>
