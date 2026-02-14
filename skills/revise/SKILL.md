---
name: revise
description: Unified revise for plans OR specs. Auto-detects target from critique
  report. Use when "revise", "fix plan/specs", or after /critique returns FIX_AND_SHIP.
  For initial creation, use /plan instead.
argument-hint: <project-name>
inherit:
- review
tools:
- auggie
- warpgrep
ultrathink: true
required_todos:
- load-critique
- extract-blockers
- verify-before-fixing
- apply-fixes
- verify-fixes
- output
---

<role>
WHO: Revision executor
ATTITUDE: A partial P0 fix is no fix. ALL blockers addressed or workers will fail.
</role>

<purpose>
Read critique findings, verify each against codebase, apply fixes, confirm blockers resolved.
</purpose>

<workflow>

## Step 1: Load Critique + Context Validation
<!-- steps/load-critique.md -->
Read steps/load-critique.md and execute Phase 0 (skill_init, plan loading, finding extraction) and Phase 0.5 (user confirmation).

## Step 2: Extract Blockers
<!-- steps/extract-blockers.md -->
Read steps/extract-blockers.md and execute Phase 1 (group by priority, display P0/P1 counts, all mandatory).

## Step 3: Verify Before Fixing
<!-- steps/verify-findings.md -->
Read steps/verify-findings.md and execute Phase 2 (grep codebase, VALID/INVALID/STALE marking, new findings).

## Step 4: Apply Fixes
<!-- steps/apply-fixes.md -->
Read steps/apply-fixes.md and execute Phase 3 (PLAN fixes with resolution, CriterionV2 history, SPECS in-place edits).

## Step 5: Verify + Output
<!-- steps/verify-resolution.md -->
Read steps/verify-resolution.md and execute Phase 4 (lightweight re-checks) and Phase 5 (publish report, findings table, git commit).

</workflow>

<rules>
- Verify EVERY finding against codebase BEFORE fixing -- critiques lie
- VALID/INVALID/STALE marking is MANDATORY -- document evidence
- ALL P0s AND P1s must be resolved (partial = fail)
- Plan revisions update in place, set resolution on history entries (fixed/rejected/deferred)
- Spec revisions edit in place
- Don't expand scope -- fix only what critique found (but fix it completely when verification reveals larger scope)
</rules>
