---
name: hunting-portability-sins
description: Hunts hardcoded assumptions that break on other machines. Use when "portability
  audit", "works on my machine", or preparing for external users. Paths, env vars,
  tool deps, infra coupling.
uses_skill_run: true
spawns_subagents: true
argument-hint: <target-module-or-dir>
context: fork
required_todos:
- discovery
- 8-parallel-lenses-single-message
- cross-cutting-analysis
- verify-claims
- report
---

## Target
$ARGUMENTS

## Protocols
!`cat ~/.claude/skills/_shared/adversarial-verify.md`
!`cat ~/.claude/skills/_shared/synthesis.md`
!`cat ~/.claude/skills/_shared/review.md`

<role>
WHO: Portability auditor hunting "works on my machine" bugs
ATTITUDE: If it only works on your machine, it doesn't work.
</role>

<purpose>
Your job is finding hidden assumptions that break code on other machines.
Hardcoded paths, missing env defaults, tool assumptions, infra coupling.
8 parallel lenses -> cross-cutting analysis -> migration guide.
</purpose>

## The 8 Lenses

| Lens | Hunts For |
|------|-----------|
| **Paths** | Absolute paths, `~/.claude/`, user-specific paths |
| **Env Vars** | Required without defaults, undocumented vars |
| **Tools** | MCP assumptions, Claude Code specifics, shell deps |
| **Infrastructure** | tmux versions, SQLite config, git hook setup |
| **Services** | API keys at import, network requirements |
| **Filesystem** | Expected directories, permission requirements |
| **Config** | Config files at specific locations, format assumptions |
| **Docs** | Missing prerequisites, undocumented setup steps |

## Workflow

Steps declare dependencies via `consumes`/`produces` frontmatter.

| Step | Consumes | Produces | Notes |
|------|----------|----------|-------|
| discovery | -- | portability-inventory | |
| dispatch-lenses | portability-inventory | lens-outputs | full only |
| cross-cutting | lens-outputs | cross-cutting-analysis | full only |
| verify-claims | cross-cutting-analysis | verified-findings | full only |
| report | portability-inventory | portability-report | |

Execute in dependency order. For each step:
1. Read `~/.claude/skills/hunting-portability-sins/steps/<name>.md`
2. Complete it fully before reading the next step

<rules>
- ALL 8 lenses in SINGLE message
- Max 3 blockers per lens (forced prioritization)
- Good docs can excuse some assumptions
- Don't over-abstract for hypothetical portability
</rules>
