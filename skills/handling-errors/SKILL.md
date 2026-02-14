---
name: handling-errors
description: Guides error handling patterns in the FormalTask codebase. Use when writing
  exception handlers, debugging silent failures, or ensuring proper error visibility.
  Activates on "error handling", "exception", "try/except", or when reviewing error-related
  code.
---

<role>
WHO: Silent failure hunter
ATTITUDE: `except: pass` is a bug factory. Every handler needs visibility.
</role>

<purpose>
Your job is to kill silent failures. Bare except handlers hide bugs for months. Every exception handler must log or re-raise—no exceptions.
</purpose>

## The Rule

**All exception handlers must have visibility.**

```python
# BAD: Silent swallowing
except ValueError:
    pass

# GOOD: Minimum DEBUG log
except ValueError as e:
    logger.debug("Parse failed, using fallback: %s", e)
```

## Exception Levels

| Level | When | Example |
|-------|------|---------|
| `ERROR` | Data loss risk, user action needed | Database write failed |
| `WARNING` | Degraded but recoverable | API retry after timeout |
| `DEBUG` | Expected fallback paths | JSON parse → markdown extraction |

## Patterns

### Database

```python
try:
    with DatabaseConnection(db_path, exclusive=True) as conn:
        cursor.execute(sql, params)
except sqlite3.IntegrityError as e:
    logger.error("Constraint violation: %s", e)
    raise
```

### File Operations

```python
try:
    with open(config_path) as f:
        config = json.load(f)
except FileNotFoundError:
    logger.debug("Config not found, using defaults: %s", config_path)
    config = DEFAULT_CONFIG
except json.JSONDecodeError as e:
    logger.warning("Invalid JSON in %s: %s", config_path, e)
    config = DEFAULT_CONFIG
```

### API Retry

```python
for attempt in range(3):
    try:
        response = api_client.request(data)
        break
    except TimeoutError:
        logger.warning("API timeout (attempt %d/3)", attempt + 1)
        if attempt == 2:
            logger.error("API failed after 3 retries")
            raise
        time.sleep(2 ** attempt)
```

## Anti-Patterns

| Pattern | Problem |
|---------|---------|
| `except: pass` | Bug hider |
| `except Exception: return None` | What failed? Why? |
| `except Exception as e: return default` | Hides TypeError, AttributeError |
| `except KeyError: logger.error(...)` | ERROR for expected path (should be DEBUG) |

## Domain Exceptions

```python
from formaltask.exceptions import TaskNotFoundError, EpicNotFoundError
from formaltask.tasks.lifecycle import InvalidTransitionError

raise TaskNotFoundError(task_id)  # Not TaskNotFoundError("msg")
```

## CLI Errors

```python
from formaltask.cli.base import CLIError
from formaltask.cli.exit_codes import ExitCode

raise CLIError("Task not found", exit_code=ExitCode.NOT_FOUND)
```

## Gotchas

| Problem | Fix |
|---------|-----|
| Silent except pass | Always log at minimum DEBUG |
| Wrong log level | ERROR = action needed, DEBUG = expected |
| Over-broad catch | Catch specific exceptions |
| Lost stack trace | Use `raise` not `raise e` |

<rules>
- Every handler logs or re-raises - no silent swallowing
- ERROR = user action needed, DEBUG = expected fallback
- Catch specific exceptions - Exception hides real bugs
- Use domain exceptions with context - `TaskNotFoundError(task_id)` not string messages
</rules>
