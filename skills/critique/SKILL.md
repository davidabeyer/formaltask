---
name: critique
description: Unified critique for plans, specs, OR task artifacts. Auto-detects target.
  Spawns auditors. Commits tasks to DB when READY. Use "critique", "review", "is this
  ready".
argument-hint: <project-name|artifact-dir> [--skip-skeptic] [--force-necessity]
inherit:
- review
tools:
- auggie
- warpgrep
spawns_subagents: true
ultrathink: true
required_todos:
- detect-target
- read-target
- check-regression-round-2-only
- spawn-auditors
- resolve-auditor-conflicts
- synthesize
- publish
---

<role>
WHO: Adversarial reviewer
ATTITUDE: Every plan solves an imaginary problem until proven otherwise.
</role>

<purpose>
Detect target type (plan/specs/task), spawn auditors who explore CODEBASE (not just read text), verify claims, synthesize verdict. For tasks: commit to DB when READY.
</purpose>

<workflow>

Steps declare dependencies via `consumes`/`produces` frontmatter.
Execute steps whose inputs are all satisfied — parallel when independent.

### Setup (sequential)
| Step | Consumes | Produces |
|------|----------|----------|
| detect-target | user-request | target-type, target-paths |
| read-target | target-type, target-paths | target-content, claims |

### TASK PATH (if target_type == TASK)
→ Read and follow: `~/.claude/skills/critique/steps/task-critique.md`
**STOP** — task path complete.

### PLAN/SPECS PATH
| Step | Consumes | Produces | Notes |
|------|----------|----------|-------|
| regression-check | target-content | regression-findings | Round 2+ only |
| spawn-auditors | target-content, target-type | auditor-findings | Parallel auditors |
| resolve-conflicts | auditor-findings | verified-findings | |
| synthesis | verified-findings, target-content | critique-verdict | |

→ Execute in dependency order. For each step:
  1. Read `~/.claude/skills/critique/steps/<name>.md`
  2. Complete it fully before reading the next step

</workflow>

## Protocols
!`cat ~/.claude/skills/_shared/review.md`

<rules>
- Auto-detect: task.md in one-offs → TASK, specs exist → SPECS, else → PLAN
- TASK path: verify paths + Context symbols, commit to DB if READY
- **Context = constraint:** If task lists "MUST use: X at file:line", verify X exists via warpgrep. Worker must use it.
- PLAN/SPECS path: full auditor workflow
- Auditors MUST explore codebase, not just read text
- Auditors spawn in SINGLE message (parallel)
- Same fix pattern = 1 blocker with count
- Verify claims BEFORE synthesis — auditors lie about tool behavior
- De-dupe overlapping findings — merge, don't stack
- **Verdict routing:** Ask user to confirm next action (APPROVED → /decompose or ft epic decompose | FIX_AND_SHIP/REVISE → /revise)
</rules>
