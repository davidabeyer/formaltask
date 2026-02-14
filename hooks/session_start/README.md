# hooks/session_start/

SessionStart hooks execute when a Claude Code session begins. They set up context, load state, and ensure the environment is ready.

## Architecture

SessionStart uses a **plain function architecture** with a single entry point (`runner.py`) that executes an ordered list of phase functions.

### Entry Point

**`runner.py`** - Single hook entry point that:
1. Reads JSON payload from stdin (contains `cwd`, `session_id`, etc.)
2. Executes all phase functions from `hooks.session_start.phases` in order
3. Continues on errors (fail-open behavior)
4. Outputs warnings to stderr on failures

### Phase Functions

Located in `hooks/session_start/phases/__init__.py`, executed in order:

| Function | Priority | Purpose |
|----------|----------|---------|
| `run_git_sync_check` | 0 | Warns if local is behind remote (runs first) |
| `run_session_metadata` | 1 | Creates session metadata in `.meta/` folder |
| `run_session_file` | 1 | Creates session file structure |
| `run_tdd_guard_init` | 1 | Initializes TDD guard state |
| `run_auto_index` | 2 | Triggers incremental codebase re-indexing |
| `run_task_context` | 2 | Loads task context for worktree agents (includes targeted sibling learnings) |
| `run_db_location_hint` | 2 | Warns about FormalTask database location |

### Phase Function Structure

Each phase is a plain function that accepts a context dict:

```python
def run_my_phase(ctx: dict) -> None:
    """Phase description.

    Args:
        ctx: Context dict with cwd, session_id, etc.
    """
    # Do phase work
    # Errors are caught by runner and logged (fail-open)
    pass
```

### Runner Pattern

```python
from hooks.session_start.phases import PHASES

def main():
    payload = json.load(sys.stdin)
    for phase_fn in PHASES:
        try:
            phase_fn(payload)
        except Exception as e:
            print(f"Warning: {phase_fn.__name__} failed: {e}", file=sys.stderr)
```

## Legacy Hooks

The following files are legacy hooks (pre-migration):

| Hook | Purpose |
|------|---------|
| `auto_fetch_origin.py` | Fetches `origin/master` to keep remote refs fresh |
| `create_session_file.py` | Creates session file |
| `create_session_metadata.py` | Creates session metadata |
| `inject_task_context.py` | Injects FormalTask context in worktrees |

## Error Handling

All phases fail open - errors are caught, logged to stderr, and execution continues with remaining phases. This ensures session start is never blocked by a single failing phase.

## Testing

```bash
pytest hooks/tests/unit/test_session_start_runner.py -v
pytest hooks/tests/unit/test_session_start_phases_implementation.py -v
```
