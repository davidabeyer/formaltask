# formaltask/utils/

Shared utilities, constants, and security helpers for FormalTask.

## Constants

Type-safe enums for status values throughout the system.

```python
from formaltask.utils.constants import TaskStatus, EpicStatus, WorkerPhase

# StrEnum - compares equal to strings
TaskStatus.IN_PROGRESS == "in_progress"  # True

# Use in queries
cursor.execute("SELECT * FROM tasks WHERE status = ?", (TaskStatus.OPEN,))
```

### TaskStatus

```
OPEN -> IN_PROGRESS -> PENDING_MERGE -> COMPLETED
                    -> PENDING_REVIEW -> COMPLETED
                    -> BLOCKED_USER -> IN_PROGRESS
                    -> BLOCKED
                    -> DEFERRED
                    -> CANCELLED
```

### Other Enums

| Enum | Values | Purpose |
|------|--------|---------|
| `EpicStatus` | PLANNING, OPEN, IN_PROGRESS, COMPLETED, ARCHIVED | Epic lifecycle |
| `WorkerPhase` | IMPLEMENTING, NEEDS_FIX, NEEDS_PR, AWAITING_MERGE, DONE, BLOCKED | Worker state |
| `FindingPriority` | P0, P1, P2, P3 | Review finding severity |
| `ReviewSeverity` | CLEAN, MINOR, MAJOR, CRITICAL | Review outcome |
| `DispositionType` | WONTFIX, NEEDSHUMAN, FIXED | Finding disposition |

## JSON Utilities

Size-limited JSON reading to prevent DoS from large inputs.

```python
from formaltask.utils.json import read_json_from_file, read_json_from_stdin

# File with 10MB limit (default)
data = read_json_from_file("config.json")

# Stdin with 50MB limit (default)
ctx = read_json_from_stdin()

# Custom limit
data = read_json_from_file("large.json", max_size=100 * 1024 * 1024)
```

### Size Limits

| Function | Default Limit | Use Case |
|----------|---------------|----------|
| `read_json_from_file()` | 10MB | General file reading |
| `read_json_from_stdin()` | 50MB | Hook context input |
| Config files | 1MB | `MAX_CONFIG_FILE_SIZE` |

## Subprocess Security

Sanitized environment for subprocess calls.

```python
from formaltask.utils.subprocess import build_subprocess_env

# Default whitelist only (PATH, HOME, USER, LANG, LC_ALL, PYTHONPATH)
env = build_subprocess_env()

# Add specific variables
env = build_subprocess_env(
    additional_vars={"API_KEY": "secret"},  # pragma: allowlist secret
    extra_whitelist=["ANTHROPIC_API_KEY"]
)

subprocess.run(["command"], env=env)
```

### Why Whitelist?

Prevents leaking sensitive or attacker-controlled environment variables to subprocesses. Only explicitly whitelisted variables are passed.

## Key Files

| File | Purpose |
|------|---------|
| `constants.py` | TaskStatus, EpicStatus, WorkerPhase enums |
| `json.py` | Size-limited JSON reading |
| `subprocess.py` | `build_subprocess_env()` |
| `validation.py` | Input validation helpers |
| `schemas.py` | JSON schema validation |
| `skill_output.py` | Skill output formatting |

## Common Gotchas

| Issue | Solution |
|-------|----------|
| String vs enum comparison | Use `TaskStatus.OPEN` not `"open"` for type safety |
| JSON too large | Increase `max_size` or stream process |
| Missing env var in subprocess | Add to `extra_whitelist` |
| Enum not in TaskStatus | Check spelling — typos silently fail string comparison |

## See Also

- `formaltask/tasks/lifecycle.py` — Uses TaskStatus for transitions
- `formaltask/core/rules_config.py` — Uses FindingPriority
