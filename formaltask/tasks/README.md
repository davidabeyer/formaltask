# formaltask/tasks/

Task lifecycle, dependencies, and workflow enforcement for FormalTask.

## State Machine

```
                             ┌───────────┐
                             │   OPEN    │
                             └─────┬─────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
    ┌───────────┐           ┌─────────────┐           ┌───────────┐
    │ CANCELLED │◄──────────│ IN_PROGRESS │──────────►│ DEFERRED  │
    └───────────┘           └──────┬──────┘           └─────┬─────┘
          ▲                        │                        │
          │         ┌──────────────┼──────────────┐         │
          │         │              │              │         │
          │         ▼              ▼              ▼         ▼
          │   ┌───────────┐  ┌───────────┐  ┌───────────┐   │
          ├───│  BLOCKED  │  │BLOCKED_USR│  │PEND_REVIEW│   │
          │   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘   │
          │         │              │              │         │
          │         └──────────────┴──────────────┘         │
          │                        │                        │
          │                        ▼                        │
          │                 ┌─────────────┐                 │
          │                 │PENDING_MERGE│                 │
          │                 └──────┬──────┘                 │
          │                        │                        │
          │                        ▼                        │
          │                 ┌─────────────┐                 │
          └─────────────────│  COMPLETED  │◄────────────────┘
                            └─────────────┘
```

## Lifecycle Management

Single source of truth for all status transitions:

```python
from formaltask.tasks.lifecycle import transition_task_status, VALID_TRANSITIONS

# Start a task (with race protection)
success = transition_task_status(db_path, 42, "in_progress", idempotent=True)
if not success:
    print("Task already started by another process")

# Complete a task
transition_task_status(db_path, 42, "completed")

# Invalid transitions raise InvalidTransitionError
try:
    transition_task_status(db_path, 42, "open")  # Can't go backward
except InvalidTransitionError as e:
    print(f"Invalid: {e.current_status} -> {e.new_status}")
```

### Timestamp Coordination

- `in_progress` → sets `started_at` (if not already set)
- `completed` → sets `completed_at`
- Other statuses → no timestamp changes

### Exclusive Locking

Transitions use `exclusive=True` for atomic operations:

```python
with DatabaseConnection(db_path, exclusive=True) as conn:
    # Read current state and update atomically
```

## Spawnability

Determines which tasks can be spawned as workers:

```python
from formaltask.tasks.spawnability import get_spawnable_tasks

# Returns tasks ready to spawn (open status, dependencies met, no file conflicts)
spawnable = get_spawnable_tasks(cursor, epic_name)
```

### Spawn Blockers

| Blocker | Reason |
|---------|--------|
| Status not OPEN | Task already started or completed |
| Dependencies incomplete | Depends on tasks not yet completed |
| File conflict | Another in-progress task modifies same files |

### File Conflict Detection

Prevents two tasks from modifying the same files:

1. For tasks with worktrees: Uses `git diff` for actual modified files
2. For tasks without worktrees: Parses spec content for mentioned files

## Guards

Workflow enforcement to prevent invalid operations:

```python
from formaltask.tasks.guards import TaskGuards, GuardViolation

guards = TaskGuards(db_path)

try:
    guards.check_evidence_required(task_id)  # Needs commits or evidence
except GuardViolation as e:
    print(f"Blocked: {e.message}")
    print(f"Fix: {e.suggested_action}")
```

### Available Guards

| Guard | Enforces |
|-------|----------|
| `check_evidence_required` | Task has commits or completion_evidence |
| `warn_if_dependency_code_missing` | Dependency code exists in worktree |

## Dependencies

Task dependency management:

```python
from formaltask.tasks.dependencies import get_task_dependencies, check_dependencies_met

# Get dependency IDs
deps = get_task_dependencies(cursor, task_id)  # [41, 43, 45]

# Check if all dependencies completed
met, blocking = check_dependencies_met(cursor, task_id)
if not met:
    print(f"Blocked by: {blocking}")  # [{'id': 41, 'status': 'in_progress'}]
```

## Key Files

| File | Purpose |
|------|---------|
| `lifecycle.py` | `transition_task_status()`, VALID_TRANSITIONS |
| `spawnability.py` | `get_spawnable_tasks()`, file conflict detection |
| `guards.py` | TaskGuards, GuardViolation |
| `dependencies.py` | Dependency resolution |
| `crud.py` | Task CRUD operations |
| `status.py` | `check_merge_allowed()` for pre-merge hook |
| `context.py` | Task context loading |
| `operations.py` | Bulk task operations |

## Common Gotchas

| Issue | Solution |
|-------|----------|
| InvalidTransitionError | Check VALID_TRANSITIONS for allowed paths |
| Task not spawnable | Run `ft spawnable` to see blockers |
| File conflict false positive | Task has worktree but no changes — uses git diff |
| Race condition on start | Use `idempotent=True` for concurrent spawns |
| "Evidence required" | Link commits or set `completion_evidence` |

## See Also

- `formaltask/utils/constants.py` — TaskStatus enum
- `formaltask/core/` — Completion checking
- `formaltask/workers/spawner.py` — Uses spawnability checks
