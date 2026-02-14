# hooks/session_end/

SessionEnd hooks execute when a Claude Code session ends. They perform cleanup, analysis, and state persistence tasks.

## Architecture

SessionEnd uses a **plain function architecture** with a single entry point (`runner.py`) that executes phases from a list.

### Entry Point

**`runner.py`** - Single hook entry point that:
1. Reads JSON payload from stdin (contains `cwd`, `session_id`, `start_time`)
2. Skips if no `session_id` present
3. Executes phases in order from the `PHASES` list
4. Outputs empty JSON (SessionEnd never blocks)

### Phase Files

Located in `phases/` directory, registered in `phases/__init__.py`:

| Phase | Purpose |
|-------|---------|
| `doc_analyzer.py` | Analyzes session commits for documentation updates |

### Phase Structure

Each phase is a plain function:

```python
def my_phase_fn(ctx: dict) -> None:
    """Phase description.

    Args:
        ctx: stdin payload (cwd, session_id, start_time)

    SessionEnd phases should never block or raise exceptions.
    """
    # Implementation
```

Register in `phases/__init__.py`:
```python
PHASES = [my_phase_fn, ...]
```

## Legacy Files

| File | Purpose |
|------|---------|
| `doc_analyzer_worker.py` | Core logic for documentation analysis (used by phase) |
| `cleanup_orphans.py` | Cleans orphaned session data |

## Error Handling

SessionEnd is fire-and-forget: all phases fail open (errors logged but don't block session cleanup).

## Testing

```bash
pytest hooks/tests/unit/test_session_end_runner.py -v
```
