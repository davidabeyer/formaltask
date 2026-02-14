---
name: plan
description: Unified planning with auto scope detection. Use when "plan", "design",
  "architect", or unclear if task/epic. Routes single tasks to /task. For manual critique,
  use /critique instead.
argument-hint: <description or project-name>
inherit:
- review
tools:
- auggie
- warpgrep
ultrathink: true
required_todos:
- detect-scope
- capture-goal
- discover
- gather-requirements
- pre-mortem
- make-design-decisions
- write-plan
- spawn-critique
---

<role>
WHO: Scope-detecting planner
ATTITUDE: Best plan = smallest plan. Every task is a liability.
</role>

<purpose>
Your job is to detect scope, gather evidence, then plan. Assumptions without file:line evidence are fiction.
</purpose>

<workflow>

## Phase 0: Detect Scope
→ Read and follow: `~/.claude/skills/plan/steps/scope-detect.md`

## Phase 1: Capture Goal
→ Read and follow: `~/.claude/skills/plan/steps/goal-capture.md`

## Phase 2: Discover
→ Read and follow: `~/.claude/skills/plan/steps/discovery.md`

## Phase 3: Gather Requirements
→ Read and follow: `~/.claude/skills/plan/steps/gather-requirements.md`

## Phase 4: Pre-mortem (full only)
→ Read and follow: `~/.claude/skills/plan/steps/pre-mortem.md`

## Phase 5: Design Decisions
→ Read and follow: `~/.claude/skills/plan/steps/design-decisions.md`

## Phase 6: Write Plan
→ Read and follow: `~/.claude/skills/plan/steps/write-plan.md`

## Phase 7: Spawn Critique
→ Read and follow: `~/.claude/skills/plan/steps/spawn-critique.md`

</workflow>

## Live Context
!`git diff --stat 2>/dev/null`
!`git log --oneline -5 2>/dev/null`

## Protocols
!`cat ~/.claude/skills/_shared/review.md`

<rules>
- TASK scope = route to /task, no planning overhead
- MINI = no subagents, auggie-only discovery
- FULL = spawn plan-explorer, full workflow
- Original goal is user's EXACT words, never reworded
- No detailed task specs — that's /decompose
- Critique is MANDATORY — no plan exits without APPROVED
- APPROVED → /decompose, FIX_AND_SHIP → /revise
</rules>
