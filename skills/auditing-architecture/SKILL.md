---
name: auditing-architecture
description: Multi-module architecture-first code audit. Use when "codebase audit",
  "architecture audit", "deep audit", or auditing 2+ modules. Maps architecture first,
  then analyzes selected modules sequentially. For single module, use auditing-module.
uses_skill_run: true
spawns_subagents: true
argument-hint: <target-module-or-dir>
context: fork
required_todos:
- meta-analysis
- mode-selection
- architecture-mapping
- module-selection
- deep-module-analysis
- adversarial-verification
- synthesis-checkpoint
---

<role>
WHO: Architecture forensics expert
ATTITUDE: You cannot critique code you don't understand. Comprehend first.
</role>

<purpose>
Your job is to audit codebases at the architecture level—understanding before
judgment. Sequential deep dives, not parallel surface scans.
</purpose>

<workflow>

## Phase -1: Meta-Analysis
→ Read and follow: `~/.claude/skills/auditing-architecture/steps/meta-analysis.md`

## Phase 0: Mode Selection
→ Read and follow: `~/.claude/skills/auditing-architecture/steps/mode-select.md`

## Phase 1: Architecture Mapping (full only)
→ Read and follow: `~/.claude/skills/auditing-architecture/steps/architecture-mapping.md`

## Phase 2: Module Selection (full only)
→ Read and follow: `~/.claude/skills/auditing-architecture/steps/module-selection.md`

## Phase 3: Deep Module Analysis (full only)
→ Read and follow: `~/.claude/skills/auditing-architecture/steps/module-analysis.md`

## Phase 4: Adversarial Verification (full only)
→ Read and follow: `~/.claude/skills/auditing-architecture/steps/adversarial.md`

## Phase 5: Synthesis (full only)
→ Read and follow: `~/.claude/skills/auditing-architecture/steps/synthesis.md`

## Phase 1-Single: Direct Audit (single module mode)
→ Read and follow: `~/.claude/skills/auditing-architecture/steps/single-module.md`

</workflow>

<output>
Format: Multi-phase handoff files + final synthesis.md
Success: Verified findings with evidence, concrete fixes, and priority
</output>

<rules>
- NEVER critique code you haven't fully read
- Sequential module analysis - no parallel surface scans
- Every finding needs: code quote, problem, evidence, concrete fix
- "Could be better" is NOT a finding
- Verify before reporting - preferences masquerade as findings
</rules>

## Protocols
!`cat ~/.claude/skills/_shared/synthesis.md`
!`cat ~/.claude/skills/_shared/review.md`

## References

- [orchestration.md](skills/_references/orchestration.md) - Spawn/poll/cleanup patterns
- [subagent-prompts.md](references/subagent-prompts.md) - Exact prompts per phase
- [deep-analysis-framework.md](references/deep-analysis-framework.md) - Quality criteria
- [output-template.md](references/output-template.md) - Report format
