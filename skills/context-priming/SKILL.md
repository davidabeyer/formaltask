---
name: context-priming
description: 'Makes Claude a domain expert before working on code. Use when "prime
  context on", "become expert in", "deep dive into", or before debugging/building.
  Modes: Quick (no subagents), Standard (3 parallel), Deep (5 parallel), Audit (sequential
  code-indexed).'
uses_skill_run: true
spawns_subagents: true
argument-hint: <target-module-or-area>
required_todos:
- meta-analysis
- Determine goal and depth
- Execute priming
- synthesis-checkpoint
---

<role>
WHO: Project archaeology specialist
ATTITUDE: Generic advice is useless. Prime deeply or don't prime at all.
</role>

<purpose>
Transform Claude from a language expert into a PROJECT expert before real work begins.
</purpose>

## Target
$ARGUMENTS

<workflow>

## Phase 0: Meta-Analysis

**quick:** Note the target and likely goal in one sentence. Skip to Quick Mode.

**full:** Understand WHY they need priming — stated target, real question (debug/build/review?), existing knowledge, priming-vs-doing, depth hint.

## Phase 1: Ask Goal and Depth (full only)

**quick:** Skip. Default to Quick mode.

Ask two questions via AskUserQuestion:
- **Goal:** Debugging / New feature / Refactoring / Deep understanding
- **Depth:** Quick (no subagents) / Standard (3 parallel) / Deep (5 parallel) / Audit (sequential)

## Phase 2: Execute by Mode

### Quick Mode (No Subagents)
1. Load CLAUDE.md chain (Glob → Read hierarchy)
2. Semantic query: `codebase-retrieval` on target
3. Quick git: `git log --oneline -10 -- {target}`
4. Direct response with architecture summary

### Standard Mode (3 Parallel Subagents)

| Stream | Focus | Tools |
|--------|-------|-------|
| Docs+Semantic | CLAUDE.md chain, semantic search | Glob, Read, codebase-retrieval |
| Flow+Pattern | Multi-file flows, symbols | warpgrep, Grep |
| Test+History | Test files, git history | Glob, Read, Bash |

Launch all 3 as background Explore agents. Write to `{run.outputs}/stream-{N}.md`.

### Deep Mode (5 Parallel)
Standard streams + Dependencies + Integration Points.

### Audit Mode (Sequential, Code-Indexed)
1. Launch `context-priming-auditor` agent → `{run.outputs}/01-audit.md`
2. Wait, then launch `adversarial-verifier` → `{run.outputs}/02-verified.md`

**Quality gate:** Output must have actual code blocks, not "handles X" descriptions.

## Phase 3: Synthesize

**quick:** Present Key Files + Patterns + Gotchas table directly.

**full:** Read all outputs, apply sequential reasoning:
1. **File Ranking** — Critical (3+ streams), Important (2), Supporting (1)
2. **Pattern Confirmation** — Only report patterns in 2+ streams
3. **Gap Analysis** — What's missing for user's goal?

Verify: Does priming address real question? Files ranked not listed? Gotchas goal-specific?

</workflow>

<output>

```markdown
## Context Priming: {Target}
**Mode:** {Quick/Standard/Deep/Audit} | **Goal:** {goal}

### Key Files (Ranked)
| File | Purpose | Confidence |
|------|---------|------------|

### Patterns
- **{Pattern}**: {where, implications}

### Gotchas
- **{Issue}**: {why it matters}

### Ready to Help With
- [x] {Specific capability}
```
</output>

<rules>
- ALWAYS load CLAUDE.md chain first — contains project rules
- Combine semantic + flow + pattern tools — never single-tool reliance
- Include git history — shows active development
- Audit mode: actual code blocks required, not summaries
- Goal determines stream priority (debugging → tests/flow/history)
</rules>

## References
- [stream-handoffs.md](references/stream-handoffs.md) - Stream templates
- [verification-protocol.md](references/verification-protocol.md) - Audit verification
