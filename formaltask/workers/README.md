# formaltask/workers/

Worker spawning, lifecycle management, and completion gating.

## Worker Lifecycle

```
SPAWN                      SESSIONSTART                    COMPLETION
─────────────────────────────────────────────────────────────────────────
ft spawn <id>              Hook fires on session start     ft task-complete <id>
     │                              │                              │
     ▼                              ▼                              ▼
spawner.py                 task_context_loader.py          task_complete.py
     │                              │                              │
     ├─ Create worktree             ├─ Read .task/id               ├─ check_completion()
     ├─ Create branch               ├─ Load task from DB           │       │
     ├─ Write .task/ files          ├─ get_effective_config()      │       ▼
     ├─ Start tmux session          │       │                      │  fetch_completion_state()
     └─ Launch Claude               │       ▼                      │       │
                                    │  CompletionConfig            │       ▼
                                    │       │                      │  COMPLETION_RULES DSL
                                    │       ▼                      │       │
                                    └─ WorkerInstructionBuilder    │       ▼
                                            │                      └─ CompletionCheck
                                            ▼                              │
                                       Inject context                      ▼
                                       into session                 Allow or block
```

## Phase 1: Spawn

**Entry:** `ft spawn <id>` → `spawner.py:spawn_worker()`

Creates isolated worktree environment and starts Claude session.

### .task/ Binding Directory

Written to `{worktree}/.task/` for hook context injection:

| File | Content | Consumer |
|------|---------|----------|
| `id` | Task ID (e.g., `42`) | SessionStart hook |
| `project_root` | Path to main repo | Database resolution |
| `session_id` | UUID for session tracking | Session storage |
| `target_branch` | PR target branch | PR instructions |
| `chain` | Empty file (presence = true) | Autospawn chaining |

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `spawn_worker()` | `spawner.py:436` | Main entry point |
| `spawn_tmux_session()` | `spawner.py:190` | Creates tmux + launches Claude |
| `validate_task_id()` | `spawner.py` | Security validation |

## Phase 2: SessionStart

**Entry:** Claude session starts → `hooks/session_start/task_context_loader.py:process()`

Loads task context and injects instructions into agent's system prompt.

### Flow

1. Read `.task/id` to get task ID
2. Resolve database path from `.task/project_root`
3. Load task context from database
4. Call `get_effective_config(task_id, db_path)` for completion config
5. Pass config to `WorkerInstructionBuilder`
6. Return formatted context for injection

### CompletionConfig

Single source of truth for completion requirements. See `formaltask/core/README.md`.

| Field | Source | Purpose |
|-------|--------|---------|
| `required_reviews` | task metadata or global | Review types before completion |
| `require_pr` | task metadata or global | Require PR creation |
| `require_pr_merged` | task metadata or global | Require PR merged |
| `check_freshness` | global rules | Verify no new commits |
| `check_docs` | global rules | Check docs updated |
| `check_learnings` | global rules | Check learnings captured |

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `process()` | `task_context_loader.py:226` | Hook entry point |
| `format_context()` | `task_context_loader.py:162` | Builds instruction prompt |
| `get_effective_config()` | `completion_config.py:36` | Loads merged config |

## Phase 3: Completion

**Entry:** `ft task-complete <id>` → `task_complete.py:execute()`

Gates task completion based on review state and configuration.

### Flow

1. Call `check_completion(task_id, db_path)`
2. `fetch_completion_state()` gathers: reviews, PR status, findings, docs
3. Evaluate state against `COMPLETION_RULES` DSL
4. Return `CompletionCheck(allowed, phase, reason)`
5. Block if `allowed=False`, complete if `allowed=True`

### Completion Rules DSL

Rules are priority-ordered conditions in `rules_builtin.py`:

```python
BUILTIN_RULES = [
    # Rule(when, then, target, priority, name)
    Rule(when="status == cancelled", then="done", target="task.phase", priority=0, name=None),
    Rule(when="blocking_findings", then="needs_fix", target="task.phase", priority=1, name="blocking_reason"),
    Rule(when="require_pr_merged AND NOT has_pr", then="needs_pr", target="task.phase", priority=1, name="PR required"),
    # ... more rules
    Rule(when="true", then="awaiting_merge", target="task.phase", priority=999, name=None),  # Catchall
]
```

Condition syntax (rules kernel DSL):
- `key` — state[key] is truthy
- `NOT key` — state[key] is falsy
- `key == value` — state[key] == value (unquoted)
- `AND` — combine conditions

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `check_completion()` | `completion_check.py` | Main entry point |
| `fetch_completion_state()` | `completion_state.py` | Gathers all state |
| `evaluate()` | `rules.py` | Evaluates condition DSL |
| `apply_completion_rules()` | `rules_builtin.py` | Applies completion rules to state |

## Task Metadata Overrides

Workers can create tasks with metadata that overrides global completion rules:

```python
metadata = {
    "required_reviews": ["security"],  # Override default reviews
    "require_pr": False,               # Skip PR requirement
    "require_pr_merged": False,        # Skip merge requirement
    "documentation_required": True,    # Flag for doc tasks
}
```

Use case: Workers creating wontfix/out-of-scope tasks that don't need full review cycle.

## Artifact Content Flow

Spec content from `/decompose` → worker sessions:

```
/decompose                    epic_decompose.py              SessionStart Hook
────────────────────────────────────────────────────────────────────────────────
Creates spec files            Reads spec YAML content        Reads from DB
     │                              │                              │
     ▼                              ▼                              ▼
task-N-spec.yaml            metadata["artifact_content"]    context.py:55
     │                        = spec_content                       │
     │                              │                              ▼
     │                              ▼                        instructions.py:172
     └──────────────────────→ tasks.metadata               Builds worker prompt
                               (JSON column)                with spec content
```

| Stage | File | Line | Field |
|-------|------|------|-------|
| Write | `epic_decompose.py` | 134 | `metadata["artifact_content"]` |
| Store | `schema.sql` | 30 | `metadata TEXT` (JSON) |
| Read | `context.py` | 55 | `metadata.get("artifact_content")` |
| Inject | `instructions.py` | 172-184 | Appends to worker instructions |

## Key Files

| File | Purpose |
|------|---------|
| `spawner.py` | Worker spawning (worktree, tmux, Claude) |
| `instructions.py` | WorkerInstructionBuilder |
| `resume.py` | Worker resume after blocking |
| `disposition.py` | Review finding dispositions |
| `health.py` | Worker health monitoring |
| `inbox.py` | Blocked worker questions |
| `events.py` | Worker lifecycle events |
| `crash_detector.py` | Detect orphaned workers (`get_orphaned_workers`) |
| `context.py` | Session context (`get_task_id_from_session`) |

## Common Gotchas

| Issue | Solution |
|-------|----------|
| Worker gets no context | Check `.task/id` exists in worktree |
| Completion blocked unexpectedly | Run `ft spawnable` to see blockers |
| PR requirement on simple task | Set `require_pr: false` in metadata |
| Reviews not found | Check review was run against correct task ID |

## See Also

- `formaltask/core/README.md` — CompletionConfig pattern
- `hooks/CLAUDE.md` — Hook infrastructure
- `hooks/session_start/task_context_loader.py` — SessionStart implementation
