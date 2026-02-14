# formaltask/state/

Worker and findings state management for FormalTask.

## Quick Start

```python
from formaltask.state.findings import check_findings_state, FindingsState
from formaltask.state.session import get_current_task, set_current_task

# Check if task findings block completion
state = check_findings_state(task_id, db_path)
if state.blocks_completion:
    print("Task has unresolved findings")

# Track current task per worktree
set_current_task(worktree_path, 42)
task_id = get_current_task(worktree_path)
```

## Findings State

Query and analyze review findings:

```python
from formaltask.state.findings import (
    check_findings_state,
    get_findings_with_disposition,
    FindingsState,
)

# Get full findings state
state: FindingsState = check_findings_state(task_id, db_path)
```

### FindingsState

Immutable snapshot of task findings:

```python
@dataclass(frozen=True)
class FindingsState:
    has_reviews: bool                # Has any reviews
    has_wontfix: bool                # Has WONTFIX dispositions
    has_needshuman_critical: bool    # Has P0/P1 NEEDSHUMAN
    has_needshuman_deferrable: bool  # Has P2/P3 NEEDSHUMAN
    has_unresolved_findings: bool    # Has findings without disposition
    latest_review_clean: bool        # Latest review was "clean"

    @property
    def blocks_completion(self) -> bool:
        """True if state blocks task completion."""
        return self.has_needshuman_critical or self.has_unresolved_findings
```

### Blocking Logic

| State | Blocks Completion |
|-------|-------------------|
| Unresolved findings | Yes |
| P0/P1 NEEDSHUMAN | Yes |
| P2/P3 NEEDSHUMAN | No (deferrable) |
| WONTFIX | No |
| No findings | No |

### Raw Findings Query

```python
# Get individual findings with disposition
findings = get_findings_with_disposition(task_id, db_path)
# Returns: [{"file": "x.py", "line": 10, "priority": "P1", "disposition": "wontfix"}, ...]
```

Returns findings from **latest round per review_type only** — older round findings are excluded.

## Session Tracking

Track current task per worktree:

```python
from formaltask.state.session import get_current_task, set_current_task

# Set current task for worktree
set_current_task("/path/to/worktree", 42)

# Get current task
task_id = get_current_task("/path/to/worktree")  # Returns 42 or None
```

Uses `.task/current_task` file in worktree directory.

## Transcript State

Track worker transcript modification times:

```python
from formaltask.state.manager import get_transcript_mtime

# Get last modification time of worker transcript
mtime = get_transcript_mtime(task_id, db_path)
# Returns: datetime or None
```

Used by dashboard to detect worker activity.

## Key Files

| File | Purpose |
|------|---------|
| `findings.py` | `FindingsState`, `check_findings_state()`, `get_findings_with_disposition()` |
| `session.py` | `get_current_task()`, `set_current_task()` |
| `manager.py` | `get_transcript_mtime()` |

## Common Gotchas

| Issue | Solution |
|-------|----------|
| "blocks_completion" unexpected | Check `has_unresolved_findings` — may have undispositioned findings |
| Stale findings | Only latest round findings are returned |
| Missing current_task | `.task/current_task` file not created — call `set_current_task()` |
| `FindingsState` is immutable | Create new instance for new state |

## See Also

- `formaltask/validators/gate_enforcer.py` — Uses `check_findings_state()`
- `formaltask/core/completion_state.py` — Combines findings with PR/commit state
- `formaltask/apps/dashboard/` — Uses transcript mtime for activity detection
