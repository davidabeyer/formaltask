# Linear Task Architecture

*Reference for all agents interacting with Linear tasks.*

## Status Flow

```
Later → Ready → [Cycle] → In Progress → Done
         ↓
      Waiting (blocked)
         ↓
      Icebox (quarterly)
```

**Cycle is Linear's built-in feature, not a status.** Tasks in the current cycle appear in cycle views.

## Status Definitions

| Status | Meaning | WIP Limit | Surfaces In |
|--------|---------|-----------|-------------|
| **Later** | Backlog storage. No guilt, it's just storage. | ∞ | Prioritize mode (oldest-first) |
| **Ready** | On-deck pool. "I know the first step." Candidates for this or next week. | 15-20 | Kickoff, Triage |
| **Waiting** | Blocked on external dependency. Not actionable until unblocked. | — | Kickoff (check daily) |
| **In Progress** | Actively touching right now. | 3 max | Kickoff |
| **Done** | Completed. | — | End of Day |
| **Canceled** | Archived - this isn't happening, stop pretending. | — | — |
| **Icebox** | Someday/maybe. Out of regular rotation. | ∞ | Quarterly review only |

## Critical Semantics

### Ready ≠ "Scoped"

**Ready means temporal proximity, NOT completeness.**

- Ready = "I'm considering this in the next 1-2 weeks"
- Ready ≠ "This is fully broken down and actionable"

Scoping/breakdown happens during Kickoff Phase 4, not as a status gate. An item can be Ready but still need decomposition help.

### Cycle = This Week

Linear's cycle feature handles weekly commitment. Tasks in cycle = "I'm doing this THIS WEEK."

Promotion to cycle happens during:
- Kickoff: selecting focus items
- Triage: adding Ready items to this week

## WIP Limits (Skill-Enforced)

Linear doesn't enforce WIP limits natively. The planning skill warns when limits exceeded.

| Column | Limit | Enforcement |
|--------|-------|-------------|
| Ready | 15-20 | Warn in Triage if exceeded. Force demote or promote. |
| In Progress | 3 | Warn in Kickoff. Can't start new without finishing/parking. |
| Cycle | 7-10 | Warn in Kickoff. "That's a lot for one week." |

**When Ready exceeds 20:** Prioritize mode forces decision - demote to Later or promote to Cycle.

## Prioritization Model

**Status flow IS priority. No priority field needed.**

| Status | Commitment Level |
|--------|------------------|
| Later | None - just storage |
| Ready | Acknowledged - should do soon |
| Cycle | Weekly commitment |
| Focus (3 items) | Daily commitment |

**Due dates override everything.** If urgent, add to Cycle. The act of adding IS the prioritization.

## Entity Types (Not Everything Is a Task)

Some items don't fit the task flow. Handle them differently:

| Type | Where | How It Surfaces |
|------|-------|-----------------|
| **True tasks** | Linear statuses | Normal Later→Ready→Cycle→Done flow |
| **Breakdown-needed** | Breakdown label | Kickoff Phase 2.5 before focus selection |
| **Blocked items** | Waiting status | Kickoff daily check |
| **Research/learning** | Later or Obsidian | Consider if it's a task or a note |

## Scripts Reference

```bash
# Status changes
update-task.sh DAB-XXX --status "Ready"
update-task.sh DAB-XXX --status "Done"
update-task.sh DAB-XXX --add-to-cycle

# Special destinations
archive-task.sh DAB-XXX "reason"          # → Canceled
icebox-task.sh DAB-XXX "reason"           # → Icebox project

# Fetch by status
get-later-items.sh                        # All Later items by project
get-ready-backlog.sh                      # Ready items not in cycle
get-cycle-issues.sh                       # Cycle + waiting + due soon
```

## Mode Reference

| Mode | Scope | Primary Action |
|------|-------|----------------|
| **Kickoff** | Cycle + overdue | Pick 3 focus items for today |
| **Triage** | Ready not in cycle | Decide what to add to this week's cycle |
| **Prioritize** | Later items | Decide fate: promote, keep, icebox, or kill |
| **End of Day** | Today's plan | Reflect, sync completions, update streaks |

## Forcing Functions

The system only works if these run regularly:

| Ritual | Frequency | What It Does |
|--------|-----------|--------------|
| Prioritize | Weekly minimum | Surfaces Later items oldest-first. Forces decision. |
| Kickoff | Daily | Commits to focus items within time budget. |
| End of Day | After work sessions | Syncs completions, captures patterns. |

**If Prioritize doesn't run weekly, Later becomes a guilt pile.** That's the primary forcing function.
