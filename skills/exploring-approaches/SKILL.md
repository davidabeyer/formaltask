---
name: exploring-approaches
description: Explores multiple implementation approaches in parallel before committing
  to one. Use when user requests a new feature, "plan this", "how should I implement
  X", or when there are multiple valid ways to solve a problem. Spawns 3 orthogonal
  explorer personas (Simple, Scalable, Balanced) for unbiased comparison.
uses_skill_run: true
argument-hint: <feature-or-decision>
context: fork
required_todos:
- meta-analysis
- initialize
- requirements
- context
- spawn-explorers-parallel
- adversarial-synthesis
- plan-checkpoint
---

<role>
WHO: Implementation scout
ATTITUDE: First idea wins by default. Kill the default.
</role>

<purpose>
Your job is to prevent single-approach blindness. Spawn 3 orthogonal explorers—Simple, Scalable, Balanced—then let the user choose. No recommendations until all three report back.
</purpose>

## The Three Explorers

| Persona | Question | Territory |
|---------|----------|-----------|
| **Simple** | "What's the FASTEST path?" | Minimal viable, quick wins, refactor later |
| **Scalable** | "What's the ROBUST path?" | Production-ready, handles growth |
| **Balanced** | "What's the PRAGMATIC path?" | Middle ground, strategic cuts |

Each advocates genuinely. No straw men.

---

## Workflow

Steps declare dependencies via `consumes`/`produces` frontmatter.
Execute steps whose inputs are all satisfied — parallel when independent.

| Step | Consumes | Produces | Notes |
|------|----------|----------|-------|
| meta-analysis | user-request | real-decision, constraints | |
| initialize | real-decision | skill-run | |
| requirements | skill-run | requirements, success-criteria | |
| context | requirements | codebase-context | |
| spawn-explorers | requirements, codebase-context | approach-analyses | fan_out: 3 explorers, full only |
| synthesis | approach-analyses, real-decision | comparison, chosen-approach | |
| plan | chosen-approach, requirements | implementation-plan | |

→ Execute in dependency order. For each step:
  1. Read `~/.claude/skills/exploring-approaches/steps/<name>.md`
  2. Complete it fully before reading the next step

---

## Explorer Output Format

Each writes JSON to `{run.outputs}/{persona}-explorer.json`:

```json
{
  "persona": "simple|scalable|balanced",
  "approach_name": "...",
  "philosophy": "One sentence",
  "implementation_steps": [{"step": 1, "action": "...", "file": "path:line"}],
  "files_affected": [{"file": "...", "change_type": "new|modify|delete"}],
  "pros": ["..."],
  "cons": ["..."],
  "risks": [{"risk": "...", "mitigation": "..."}],
  "effort": "low|medium|high",
  "tech_debt": "none|minor|significant"
}
```

<rules>
- Three explorers, single message - parallel or nothing
- Each persona advocates genuinely - straw men are lies
- Wait for user choice - never pick for them
- Every approach has cons - hiding them is sabotage
</rules>
