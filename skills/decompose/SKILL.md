---
name: decompose
description: Decompose plan -> specs OR specs -> tasks. Auto-detects stage. Use when
  "decompose", "break down", or after /critique APPROVED. For initial planning, use
  /plan instead.
argument-hint: <project-name>
inherit:
- review
tools:
- auggie
- warpgrep
spawns_subagents: true
ultrathink: true
required_todos:
- detect-stage-action
- codebase-context
- execute-decomposition
- output
---

<role>
WHO: Decomposition executor
ATTITUDE: 10 tiny tasks is worse than 3 right-sized ones. Every criterion must survive the deletion test.
</role>

<purpose>
Your job is to detect stage (plan→specs or specs→tasks), gather codebase context, and execute decomposition with right-sized tasks.
</purpose>

<workflow>

## Phase 0: Detect Stage
→ Read and follow: `~/.claude/skills/decompose/steps/detect-stage.md`

## Phase 1: Codebase Context
→ Read and follow: `~/.claude/skills/decompose/steps/context-gather.md`

## Phase 2: Execute Decomposition

### If PLAN_TO_SPECS:
→ Read and follow: `~/.claude/skills/decompose/steps/decompose-specs.md`

### If SPECS_TO_TASKS:
→ Read and follow: `~/.claude/skills/decompose/steps/decompose-tasks.md`

## Phase 3-4: Quality Review & Output
→ Read and follow: `~/.claude/skills/decompose/steps/quality-review.md`

</workflow>

## Anti-Patterns

| Wrong | Right |
|-------|-------|
| 10 tiny tasks | 3 right-sized tasks |
| 15 criteria per task | 3-5 essential behavioral tests |
| "Works correctly" | Testable assertions |
| No integration tests | Include integration criteria in relevant tasks |
| Dotted IDs (1.1) | Sequential integers (1, 2, 3) |
| Split TDD phases | Atomic TDD within each task (see TDD Atomicity above) |
| TBD/TODO in spec | Resolve now or ask user |
| Missing implements | Every task links to plan goal IDs |
| Phases with import deps between them | Each phase ships independently — merge if symbol created in N used in N |
| Manual `depends_on` when task references another's output | Use `inputs: {key: "$task[N].outputs.key"}` — deps auto-computed |
| String criteria (`- "text"`) | CriterionV2 format (`- id: c-1, current: "text"`) |
| Dict testing (`testing: {unit: ...}`) | List testing (`testing: ["unit: ..."]`) |

## Protocols
!`cat ~/.claude/skills/_shared/review.md`

<rules>
- Auto-detect: specs exist → specs→tasks, else → plan→specs
- MCP codebase context is MANDATORY before decomposing
- Every criterion must pass Beck's deletion test
- Hard limits: 3-5 unit, 1-2 integration, 0 E2E per task
- **Auto-infer deps via inputs/outputs** — `$task[N].outputs.key` in inputs auto-adds N to depends_on. Use manual `depends_on` only for ordering-only constraints.
- **implements field MANDATORY:** Each spec/task links to plan goal IDs (e.g., implements: ["g-1"])
- **CriterionV2 format MANDATORY:** Each criterion must have `id: c-N`, `current: "text"`, optional `command:`. Simple strings REJECTED by hook.
- **testing field MANDATORY list[str]:** NOT a dict. Format: `testing: ["unit: description", "integration: description"]`. Dict format REJECTED by Pydantic.
- **Model Field Consumer Rule:** TaskSpec fields must have consumer code in epic_decompose.py (tested by tests/unit/test_model_field_consumers.py)
- Task numbering: sequential integers only
- ft epic decompose for final DB commit (not direct writes)
</rules>
