---
name: auditing-style
description: Deep style audit with 6 sequential passes (naming, typing, pythonic,
  organization, docs, modernization). Use when "style audit", "is this Pythonic",
  or "style debt". For architecture, use auditing-architecture.
uses_skill_run: true
spawns_subagents: true
argument-hint: <target-module>
context: fork
required_todos:
- mode-selection
- load-status
- present-target
- mark-in-progress
- exhaustive-reading
- sequential-passes-not-parallel
- verification
- synthesize
- update-tracker-final
---

<role>
WHO: Style auditor running 6 sequential passes
ATTITUDE: Style issues compound. A `d` variable is a paper cut. 50 paper cuts is death.
</role>

<purpose>
Your job is finding ALL style issues in one module deeply. Not many shallowly.
Sequential passes build context: naming -> typing -> pythonic -> org -> docs -> modern.
</purpose>

## Phase 0: Mode Selection
-> Read and follow: `~/.claude/skills/auditing-style/steps/mode-select.md`

## Phase 1: Load Status
-> Read and follow: `~/.claude/skills/auditing-style/steps/load-status.md`

## Phase 2: Present Target
-> Read and follow: `~/.claude/skills/auditing-style/steps/present-target.md`

## Phase 3: Mark In-Progress
-> Read and follow: `~/.claude/skills/auditing-style/steps/mark-progress.md`

## Phase 4: Exhaustive Reading (full only)
-> Read and follow: `~/.claude/skills/auditing-style/steps/exhaustive-read.md`

## Phase 5: Sequential Passes (full only)
-> Read and follow: `~/.claude/skills/auditing-style/steps/sequential-passes.md`

## Phase 6: Verification (full only)
-> Read and follow: `~/.claude/skills/auditing-style/steps/verification.md`

## Phase 7: Synthesize
-> Read and follow: `~/.claude/skills/auditing-style/steps/synthesis.md`

## Phase 8: Update Tracker
-> Read and follow: `~/.claude/skills/auditing-style/steps/update-tracker.md`

---

## Severity

| Level | Criteria | Example |
|-------|----------|---------|
| P0 | Causes bugs NOW | Type says `str`, returns `None` |
| P1 | Maintenance pain | Inconsistent naming |
| P2 | Reduces readability | Missing docstring |
| P3 | Style preference | `os.path` vs pathlib |

Most findings are P2/P3. If everything is P0, recalibrate.

## Protocols
!`cat ~/.claude/skills/_shared/synthesis.md`
!`cat ~/.claude/skills/_shared/review.md`

<rules>
- ONE module max (split larger audits)
- Sequential passes, NOT parallel
- Every finding needs file:line
- Actual code in handoffs, not summaries
</rules>
