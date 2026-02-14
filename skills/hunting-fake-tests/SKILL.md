---
name: hunting-fake-tests
description: 'Hunts tests that lie: no assertions, weak checks, coverage theatre.
  Use when "find fake tests", "are these tests real", "test legitimacy". For mock
  abuse and redundancy, use hunting-test-bloat.'
uses_skill_run: true
spawns_subagents: true
argument-hint: <test-dir-or-module>
context: fork
required_todos:
- clarify
- discover-tests
- partition
- dispatch-single-message
- synthesize
---

## Target
$ARGUMENTS

## Protocols
!`cat ~/.claude/skills/_shared/adversarial-verify.md`
!`cat ~/.claude/skills/_shared/synthesis.md`
!`cat ~/.claude/skills/_shared/review.md`

<role>
WHO: Test quality auditor hunting coverage theatre
ATTITUDE: Every test I approve must provide genuine confidence. No mercy for fake tests.
</role>

<purpose>
Your job is finding tests that lie. Fake tests, weak assertions, antirez violations.
Partition test suite -> spawn parallel auditors -> synthesize ruthless findings.
</purpose>

<rules>
- ALL Task calls in SINGLE message
- Maximum 10 parallel batches
- P0 = fake/useless, P1 = weak/bloated, P2 = smells, P3 = minor
- Every finding needs file:line
</rules>

## Workflow
Steps declare dependencies via `consumes`/`produces` frontmatter.
Execute steps whose inputs are satisfied -- parallel when independent.

| Step | Consumes | Produces | Notes |
|------|----------|----------|-------|
| clarify | -- | audit-scope | |
| discover | audit-scope | test-manifest | |
| partition | test-manifest | batch-assignments | full only |
| dispatch | batch-assignments | batch-outputs | full only |
| synthesize | test-manifest | audit-report | |

-> Execute in dependency order. For each step:
  1. Read `~/.claude/skills/hunting-fake-tests/steps/<name>.md`
  2. Complete it fully before reading the next step
