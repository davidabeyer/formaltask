# Skill Span Tracking

How Claude Code tracks which skill steps have been visited, enforces step ordering, and manages skill composition.

## The problem

Skills can be decomposed into ordered steps with dependencies. When Claude reads step files, the system needs to:

1. **Enforce ordering** — block step C if it depends on output from step B, which hasn't run yet
2. **Track progress** — know which steps have been visited in the current skill invocation
3. **Handle composition** — skill A can invoke skill B mid-flow, then resume A
4. **Survive subprocess boundaries** — each hook invocation is a fresh Python process

## Architecture

Three hooks cooperate around a single source of truth (`skill_span` table in the skill tracking database):

```
Claude reads a step file
        │
        ▼
┌─────────────────────┐     ┌──────────────────────┐
│  PreToolUse hook     │     │     skill tracking DB  │
│  (step_gate.py)      │────▶│                      │
│                      │     │  skill_span table:   │
│  "Has step B been    │◀────│  - span_id           │
│   visited yet?"      │     │  - skill             │
│                      │     │  - status (active/   │
│  Block or allow.     │     │    suspended/done)   │
└─────────────────────┘     │  - steps ["a","b"]   │
                             │  - parent_span_id    │
Claude reads the file        │                      │
        │                    └──────────┬───────────┘
        ▼                               │
┌─────────────────────┐                 │
│  PostToolUse hook    │                 │
│  (step_logger.py)    │─── writes ─────┘
│                      │
│  "Record that step   │
│   B was visited."    │
└─────────────────────┘

Session ends
        │
        ▼
┌─────────────────────┐
│  SessionEnd hook     │
│  (phases/__init__)   │
│                      │
│  Complete all active │
│  spans. Clean slate. │
└─────────────────────┘
```

**No module-level state.** Each hook subprocess queries the DB fresh. No stack files, no in-memory caches for span state.

## Database schema

```sql
CREATE TABLE skill_span (
    span_id         TEXT PRIMARY KEY,
    skill           TEXT NOT NULL,
    parent_span_id  TEXT,           -- NULL = root, set = composed
    status          TEXT NOT NULL DEFAULT 'active',
    first_step      TEXT,
    last_step       TEXT,
    steps           TEXT DEFAULT '[]',  -- JSON array of visited step names
    started_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    suspended_at    TEXT,
    completed_at    TEXT,
    FOREIGN KEY (parent_span_id) REFERENCES skill_span(span_id)
);
```

Status lifecycle: `active` → `suspended` (skill switch) → `active` (resume) → `completed` (session end).

## Step file frontmatter

Step files declare their dependencies via YAML frontmatter:

```markdown
---
consumes: [hunt-target, code-topology]
produces: [hunt-findings]
optional: true
---
# Hunt Phase

Do the actual hunting...
```

| Field | Type | Purpose |
|-------|------|---------|
| `consumes` | list | Artifacts this step needs (must be produced by a prior step) |
| `produces` | list | Artifacts this step creates (unlocks downstream steps) |
| `optional` | bool | If true, downstream steps aren't blocked when this step is skipped |

The special artifact `user-request` is always satisfied — root steps consume only this.

## The three hooks

### 1. Step gate (PreToolUse) — the reader

**File:** `hooks/pretool/phases/step_gate.py`

When Claude reads `~/.claude/skills/{skill}/steps/{step}.md`:

1. Parse all step files in the skill to build a dependency graph (cached per skill)
2. Query DB for the active span's visited steps
3. Check if all consumed artifacts have been produced by visited steps
4. Block with reason if dependencies are missing; allow otherwise

```python
# The core query — single source of truth
row = db.execute(
    "SELECT steps FROM skill_span "
    "WHERE skill = ? AND status = 'active' "
    "ORDER BY started_at DESC LIMIT 1",
    (skill,),
).fetchone()
```

**Fail-open guarantee:** Any exception returns `[]` (empty visited list), which allows root steps and blocks nothing when the DB is down.

### 2. Step logger (PostToolUse) — the writer

**File:** `hooks/posttool/phases/step_logger.py`

After Claude successfully reads a step or SKILL.md file:

1. **Detect skill switch** — query for active spans belonging to a different skill. If found, suspend it and emit `session_end` event.
2. **Get or create span** — three branches:
    - **Active span exists:** append the step to its `steps` array
    - **Suspended span exists:** resume it (set status back to active), append step
    - **No span:** create a new one, detect parent from other active/suspended spans
3. **Emit events** — `step_enter` for the step, `session_start`/`session_end` for skill transitions
4. **Context injection** — return `additionalContext` if the step has been visited >10 times (pace warning) or if the span has a parent (ancestry context)

### 3. Session end — the cleaner

**File:** `hooks/session_end/phases/__init__.py`

When a conversation ends:

1. Emit `session_end` event for any skill still open
2. **Complete ALL active spans** — prevents cross-session bleed where a stale span from a crashed session causes the gate to over-permit

```python
db.execute(
    "UPDATE skill_span SET status = 'completed', "
    "completed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
    "WHERE status = 'active'"
)
```

## Skill composition

When skill A invokes skill B:

```
skill A: span-aaa (active)
  └── skill B: span-bbb (active, parent_span_id = span-aaa)
```

The parent pointer is set by querying for the most recent active/suspended span from a *different* skill when creating a new span. This enables:

- **Ancestry context** — when entering from a parent skill, the logger injects `[Entered from {parent} — be brief, context already loaded.]`
- **Independent tracking** — each skill has its own span with its own steps array

When switching back from B to A:

1. B's span is suspended
2. A's span is resumed (found as suspended root span)
3. Steps continue appending to A's span

## Dependency graph example

Given a skill with these steps:

```
clarification:  consumes [user-request]     produces [hunt-target]
topology:       consumes [hunt-target]       produces [code-topology]
hunt:           consumes [hunt-target,       produces [hunt-findings]
                          code-topology]
synthesis:      consumes [hunt-findings]     produces [report]
```

The gate enforces this ordering:

```
clarification ──▶ topology ──▶ hunt ──▶ synthesis
       │                        ▲
       └────────────────────────┘
```

- `clarification` always allowed (consumes only `user-request`)
- `topology` blocked until `clarification` visited
- `hunt` blocked until both `clarification` AND `topology` visited
- `synthesis` blocked until `hunt` visited

## Monolithic vs decomposed skills

| Type | Detection | Span behavior |
|------|-----------|---------------|
| **Monolithic** | `*/skills/{skill}/SKILL.md` read | Single-step span with `first_step = "SKILL"` |
| **Decomposed** | `*/skills/{skill}/steps/{step}.md` read | Multi-step span, steps appended in visit order |

Both types create spans. The gate only activates for decomposed skills (only step files have frontmatter to check).

## Failure modes

| Scenario | Behavior | Why it's safe |
|----------|----------|---------------|
| DB locked | Gate returns `[]` → allows all steps | Fail-open prevents false blocks |
| DB corrupt | Same as locked | Same |
| Stale active span from crash | Gate sees old steps → may over-permit | Acceptable — session end cleans up |
| Multiple active spans (bug) | `LIMIT 1` picks latest | Deterministic, latest wins |
| Concurrent sessions | Each session creates its own span | Isolated by span_id |
| Step without frontmatter | No `consumes` → always allowed | Graceful degradation |
| Internal skill (`_partials/`) | Skipped entirely | These are template fragments |

**Design principle:** The gate never produces a false block. In ambiguous situations, it allows the step through.

## Files

| File | Role |
|------|------|
| `hooks/pretool/phases/step_gate.py` | PreToolUse — dependency checking |
| `hooks/posttool/phases/step_logger.py` | PostToolUse — span creation/updates |
| `hooks/session_end/phases/__init__.py` | SessionEnd — span completion |
| `formaltask/db/connection.py` | Database connection and schema |
| `~/.claude/skills/{skill}/steps/*.md` | Step files with frontmatter |
| `tests/unit/hooks/test_step_gate.py` | Gate tests (19 tests) |
| `tests/unit/hooks/test_step_logger.py` | Logger tests (13 tests) |

## Authoring a decomposed skill

To add dependency enforcement to a skill:

1. Create a `steps/` directory inside your skill
2. Add step files with YAML frontmatter:

    ```markdown
    ---
    consumes: [user-request]
    produces: [gathered-data]
    ---
    # Gather

    Instructions for the gather phase...
    ```

3. Chain dependencies through artifacts:

    ```markdown
    ---
    consumes: [gathered-data]
    produces: [analysis]
    ---
    # Analyze

    Instructions for the analysis phase...
    ```

4. Mark optional steps that can be skipped:

    ```markdown
    ---
    consumes: [gathered-data]
    produces: [verified-data]
    optional: true
    ---
    # Verify (optional)
    ```

The gate will automatically enforce that Claude reads steps in a valid topological order.
