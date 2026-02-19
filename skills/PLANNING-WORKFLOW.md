# Planning Workflow

Complete workflow for planning, critiquing, revising, and decomposing projects.

```
                          PLANNING LIFECYCLE
═══════════════════════════════════════════════════════════════════════

  ┌─────────┐     ┌───────────┐     ┌─────────┐     ┌─────────────┐
  │  /plan  │────▶│ /critique │────▶│ /revise │────▶│ /decompose  │
  └─────────┘     └───────────┘     └─────────┘     └─────────────┘
       │               │                 │                 │
       │               │                 │                 │
       ▼               ▼                 ▼                 ▼
  ┌─────────┐     ┌───────────┐     ┌─────────┐     ┌─────────────┐
  │  PLAN   │     │  INLINE   │     │ REVISED │     │    SPECS    │
  │  .yaml  │     │  history  │     │  .yaml  │     │   .yaml     │
  └─────────┘     └───────────┘     └─────────┘     └─────────────┘
       │               │                 │                 │
       ▼               ▼                 ▼                 ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                         GIT HISTORY                              │
  │  plan: project round 1                                           │
  │  critique: project plan round 1 - APPROVED                       │
  │  revise: project round 1                                         │
  │  decompose: project plan→specs                                   │
  │  critique: project specs round 1 - APPROVED                      │
  └─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   /plan-status         │
                    │   Dashboard view       │
                    └────────────────────────┘

═══════════════════════════════════════════════════════════════════════
```

## Quick Reference

| Stage | Command | Git Commit | Next Step |
|-------|---------|------------|-----------|
| Create plan | `/plan {project}` | `plan: {project} round N` | `/critique` |
| Review plan | `/critique {project}` | `critique: {project} plan round N - VERDICT` | See verdict |
| Fix blockers | `/revise {project}` | `revise: {project} round N` | `/critique` |
| Generate specs | `/decompose {project}` | `decompose: {project} plan→specs` | `/critique` |
| Review specs | `/critique {project}` | `critique: {project} specs round N - VERDICT` | See verdict |
| Create tasks | `ft epic decompose` | (DB, not git) | `ft work spawn` |

## Verdict Routing

```
                    ┌─────────────────────────────────────┐
                    │           /critique                 │
                    │                                     │
                    │   Verdict?                          │
                    └──────────────┬──────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
           ▼                       ▼                       ▼
    ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
    │   APPROVED   │       │ FIX_AND_SHIP │       │    REVISE    │
    │              │       │              │       │              │
    │  0 blockers  │       │  1-2 fixable │       │  3+ or major │
    └──────┬───────┘       └──────┬───────┘       └──────┬───────┘
           │                       │                       │
           ▼                       └───────────┬───────────┘
    ┌──────────────┐                           │
    │  Plan?       │                           ▼
    │  → /decompose│               ┌───────────────────────┐
    │              │               │       /revise         │
    │  Specs?      │               │                       │
    │  → ft epic   │               │  Fix blockers, then   │
    │    decompose │               │  re-run /critique     │
    └──────────────┘               └───────────────────────┘
```

## File Layout

All planning artifacts live in `~/projects/{project}/plans/`:

```
~/projects/{project}/
└── plans/
    ├── {project}-plan.yaml              # Plan with inline critique history
    └── specs/
        ├── task-1-setup-spec.yaml
        ├── task-2-implement-spec.yaml
        └── task-3-verify-spec.yaml
```

**Inline Critique Format:** Critique data is stored in goal history, not separate `.md` files:
```yaml
goals:
  - id: "g-1"
    current: "Feature works correctly"
    history:
      - version: "r1"
        text: "Feature works correctly"
        critique:
          verdict: "FIX_AND_SHIP"
          findings:
            - priority: "P1"
              finding: "Missing validation"
              action: "Add input validation"
              resolution: "fixed"  # Set by /revise
```

## Git Commit Formats

All commits follow a consistent format for tracking:

```bash
# Plan creation
plan: {project} round {N}

# Critique (includes target type)
critique: {project} plan round {N} - {APPROVED|FIX_AND_SHIP|REVISE}
critique: {project} specs round {N} - {APPROVED|FIX_AND_SHIP|REVISE}

# Revision
revise: {project} round {N}

# Decomposition
decompose: {project} plan→specs
```

## Status Dashboard

Run `/plan-status` to see all projects and their current stage:

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
  billing         plan round 1              → /critique
  test-versioning decompose plan→specs      → /critique

═══════════════════════════════════════════════════════════════
```

## Complete Example

```bash
# 1. Create plan
/plan my-feature
# → Writes ~/projects/my-feature/plans/my-feature-plan.yaml
# → Commits: "plan: my-feature round 1"
# → Auto-spawns /critique

# 2. Critique finds issues (FIX_AND_SHIP)
# → Commits: "critique: my-feature plan round 1 - FIX_AND_SHIP"
# → User chooses /revise

# 3. Revise fixes blockers
/revise my-feature
# → Writes ~/projects/my-feature/plans/my-feature-plan-v2.yaml
# → Commits: "revise: my-feature round 1"
# → User runs /critique again

# 4. Critique approves
# → Commits: "critique: my-feature plan round 2 - APPROVED"
# → User chooses /decompose

# 5. Decompose to specs
/decompose my-feature
# → Writes specs/*.yaml
# → Commits: "decompose: my-feature plan→specs"
# → User runs /critique to review specs

# 6. Specs approved
# → Commits: "critique: my-feature specs round 1 - APPROVED"
# → User runs ft epic decompose

# 7. Create tasks in DB
ft epic decompose my-feature ~/projects/my-feature/plans/specs/
# → Tasks created in FormalTask DB
# → Ready to spawn workers
```

## Transition to FormalTask

After specs are approved and committed to DB:

```
     PLANNING PHASE                      EXECUTION PHASE
          (Git)                              (DB)
            │                                  │
  ┌─────────┴─────────┐            ┌──────────┴──────────┐
  │                   │            │                     │
  │  /plan            │            │  ft epic decompose  │
  │  /critique        │     ──▶    │  ft work spawn           │
  │  /revise          │            │  ft task complete   │
  │  /decompose       │            │  ft task list       │
  │  /plan-status     │            │                     │
  │                   │            │                     │
  └───────────────────┘            └─────────────────────┘
        ~/projects/                   .claude/formaltask.db
         git repo                          SQLite
```

## Skills Reference

| Skill | Purpose | Location |
|-------|---------|----------|
| `plan` | Create/update project plans | `~/.claude/skills/plan/` |
| `critique` | Review plans or specs for issues | `~/.claude/skills/critique/` |
| `revise` | Fix blockers from critique | `~/.claude/skills/revise/` |
| `decompose` | Break plan into specs or specs into tasks | `~/.claude/skills/decompose/` |
| `plan-status` | Dashboard of all projects | `~/.claude/skills/plan-status/` |
