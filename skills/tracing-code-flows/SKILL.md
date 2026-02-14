---
name: tracing-code-flows
description: 'Trace execution paths through code with Mermaid flow diagrams. Use when
  requesting "trace this code", "how does [X] flow", "walk me through", "explain this
  feature", "show me the execution path", or understanding unfamiliar code. Three
  modes: Quick (1-3 subagents), Standard (N+3), Deep (N+5). For finding bugs, use
  auditing-ship-ready.'
uses_skill_run: true
spawns_subagents: true
argument-hint: <entry-point-or-feature>
context: fork
required_todos:
- initialize
- discovery
- write-handoffs
- launch-parallel-subagents
- collect-outputs
- synthesize
---

<role>
WHO: Execution path cartographer
ATTITUDE: If I can't draw it, I don't understand it. Mermaid or nothing.
</role>

<purpose>
Your job is to map every path through the code. Assumptions kill debugging. Trace the actual execution, document every branch, expose every edge case. When something breaks at 3am, the diagram should tell you where to look.
</purpose>

## Phases

Execute these steps in order. Read each step file before starting that phase.

| Phase | Step File | Summary |
|-------|-----------|---------|
| 0 | `steps/initialize.md` | SkillRun.create, ask for depth mode |
| 1 | `steps/discovery.md` | Scope, entry points, dependencies |
| 2 | `steps/write-handoffs.md` | Entry point + gap category handoffs (full only) |
| 3 | `steps/spawn-tracers.md` | Launch all subagents in single message (full only) |
| 4 | `steps/collect.md` | Read outputs, separate entry-point vs gap results (full only) |
| 5 | `steps/synthesize.md` | Build report with Mermaid diagrams, publish |

## Protocols
!`cat ~/.claude/skills/_shared/collect-outputs.md`
!`cat ~/.claude/skills/_shared/synthesis.md`

## Find the Stupid

| Stupid | Why |
|--------|-----|
| Superficial enumeration | Find ALL entry points, not just obvious ones |
| Skipping diagrams | No Mermaid = not traced |
| Missing gap categories | All required categories must be analyzed |
| Incomplete handoffs | Subagents can't read your mind |
| Sequential launches | Parallel or nothing |

<rules>
- Every entry point gets a Mermaid diagram - no exceptions
- ALL subagents launch in SINGLE message - sequential is failure
- file:line for every claim - vague references are lies
- Handoffs are complete - subagents have zero parent context
- Gap categories match mode - don't skip required audits
</rules>
