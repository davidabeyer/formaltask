---
name: adding-tasks
description: Adds tasks to FormalTask with mandatory discovery and validated criteria.
  Use when "add task", "create task", or "/task-add". For batch creation, use /epic-decompose
  instead.
argument-hint: <epic-name> [title] [--quick]
required_todos:
- validate-epic
- discovery
- validate-paths-plan-explorer
- specify
- scope-check
- determine-reviews-doc-flag
- generate-artifact
- write-artifact
- skill-review
---

<role>
WHO: Task specification analyst
ATTITUDE: A task with hallucinated paths wastes an entire work session. Unacceptable.
</role>

<purpose>
Your job is to create task artifacts with verified file paths and testable criteria.
Artifacts stay on disk until /critique-task verifies them and commits to DB.

**MANDATORY: Use TodoWrite to add these phases before starting:**
1. Validate epic exists
2. Discovery (MCP tools)
3. Validate paths (plan-explorer agent) **← MANDATORY, NO SKIPPING**
4. Specify title + criteria
5. Scope check (route to /plan if needed)
6. Determine reviews & doc flag
7. Generate artifact
8. Write artifact to disk **← STOP HERE, no DB commit**
9. Skill review **← MANDATORY**
</purpose>

<workflow>

## Phase 1: Validate Epic
→ `steps/validate-epic.md`

## Phase 2: Discovery
→ `steps/discovery.md`

## Phase 3: Validate Paths (plan-explorer)
→ `steps/validate-paths.md`

## Phase 4: Specify
→ `steps/specify.md`

## Phase 5: Scope Check
→ `steps/scope-check.md`

## Phase 6: Determine Reviews & Doc Flag
→ `steps/reviews-doc.md`

## Phase 7-8: Generate & Write Artifact
→ `steps/generate-artifact.md`

## Phase 9: Skill Review
→ `steps/skill-review.md`

</workflow>

<output>
Format: Artifact path + next command
Success: Artifact created with verified paths and testable criteria. No DB commit yet.
</output>

<rules>
- **MUST spawn plan-explorer in Phase 3** — no skipping, no rationalization
- Never proceed without ≥1 verified file path
- Reject any criterion containing vague patterns
- Flag if modifying file without corresponding test file
- Default to inbox epic with confirmation when no epic specified
- **No DB commit here** — /critique-task commits when READY
</rules>
