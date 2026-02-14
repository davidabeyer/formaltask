---
name: plan-status
description: >-
  Shows planning status dashboard for all projects. Use when "plan status",
  "what's in flight", "planning dashboard", or checking which projects need attention.
---

<role>
WHO: Planning status reporter
ATTITUDE: Stale projects rot. Surface what needs attention.
</role>

<purpose>
Your job is to query git history and show which projects are in flight and what stage they're at.
</purpose>

<workflow>

## Step 1: Query Git History

```bash
cd ~/projects && git log --oneline --all --format="%s" -200 | grep -E "^(plan|critique|revise|decompose):"
```

Parse commit messages. Formats:
- `plan: {project} round {N}`
- `critique: {project} {plan|specs} round {N} - {verdict}`
- `revise: {project} round {N}`
- `decompose: {project} plan→specs`

## Step 2: Build Project State

For each unique project found:
1. Find latest commit mentioning that project
2. Extract: stage, target (plan/specs), round, verdict (if critique)

Group by status:
- **Needs Attention**: FIX_AND_SHIP or REVISE verdict on critique
- **Ready to Proceed**: APPROVED critique (plan → /decompose, specs → ft epic decompose)
- **In Progress**: plan, revise, or decompose stage (awaiting next step)

## Step 3: Display Dashboard

```
═══════════════════════════════════════════════════════════════
   PLANNING STATUS
═══════════════════════════════════════════════════════════════

⚠️  NEEDS ATTENTION
────────────────────────────────────────────────────────────────
  auth-system     critique plan round 2     FIX_AND_SHIP
  data-migration  critique specs round 1    REVISE

✅ READY TO PROCEED
────────────────────────────────────────────────────────────────
  api-refactor    critique plan round 1     APPROVED → /decompose
  new-feature     critique specs round 1    APPROVED → ft epic decompose

🔄 IN PROGRESS
────────────────────────────────────────────────────────────────
  test-versioning decompose plan→specs      → /critique
  billing         plan round 1              → /critique

═══════════════════════════════════════════════════════════════
```

If no projects found: "No planning activity in ~/projects git history."

</workflow>

<rules>
- Query ~/projects repo only (planning commits live there)
- Latest commit per project wins (ignore older stages)
- Next action routing:
  - plan/revise → /critique
  - decompose → /critique (specs)
  - critique plan APPROVED → /decompose
  - critique specs APPROVED → ft epic decompose
  - critique FIX_AND_SHIP/REVISE → /revise
</rules>
