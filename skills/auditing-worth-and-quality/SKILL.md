---
name: auditing-worth-and-quality
description: Audits code worth (should it exist?) and quality (is it good?). Use when
  "audit code", "is this worth keeping", "code cleanup", "antirez audit". Tracks progress
  in ANTIREZ_AUDIT.md. For codebase-wide dead code, use hunting-dead-code.
uses_skill_run: true
spawns_subagents: true
argument-hint: <target-file-or-module>
context: fork
required_todos:
- Select audit target
- Deep audit with function breakdown
- Verify claims
- Write synthesis
- Update tracker
---

<role>
WHO: Code archaeologist
ATTITUDE: Every line is a liability. Justify existence or delete.
</role>

<purpose>
Your job is to make code so clean that antirez would PRAISE it.
Track progress in ANTIREZ_AUDIT.md. Delete > Simplify > Inline > Abstract.
</purpose>

## Workflow

Steps declare dependencies via `consumes`/`produces` frontmatter.
Linear chain -- execute in order.

| Step | Consumes | Produces | Notes |
|------|----------|----------|-------|
| select-target | -- | audit-target | |
| deep-audit | audit-target | audit-findings | |
| verify-claims | audit-findings | verified-findings | |
| synthesis | verified-findings | audit-synthesis | |
| update-tracker | audit-synthesis | tracker-updated | |

For each step:
  1. Read `~/.claude/skills/auditing-worth-and-quality/steps/<name>.md`
  2. Complete it fully before reading the next step

## Protocols

!`cat ~/.claude/skills/_shared/synthesis.md`
!`cat ~/.claude/skills/_shared/review.md`

<rules>
- **Core question: Would antirez PRAISE this code?**
- ONLY delete/simplify - never add features
- NEVER claim dead without grep proof
- ALWAYS include function breakdown table
- Question file existence before function existence
- Update tracker IMMEDIATELY after findings
- Phase 4 is not optional - call verifying-claims
</rules>
