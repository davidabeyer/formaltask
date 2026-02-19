# hooks/ CLAUDE.md

Hook infrastructure for Claude Code automation. Event-driven workflows triggered by Claude Code lifecycle events.

## Directory Structure

```
hooks/
├── session_start/   # SessionStart hook + phases
├── session_end/     # SessionEnd phases (currently empty)
├── stop/            # SubagentStop hook (completion enforcement)
├── pretool/         # PreToolUse validators
├── posttool/        # PostToolUse handlers (currently empty)
├── promptsubmit/    # UserPromptSubmit hooks
└── subagent_start/  # SubagentStart hooks
```

## Hook Types

| Hook | Trigger | Key Files |
|------|---------|-----------|
| SessionStart | Session begins | `session_start/phases/`, `task_context_loader.py` |
| SessionEnd | Session ends | `session_end/phases/` |
| SubagentStop | Subagent stops | `stop/phases/completion_enforcer.py` (completion enforcement) |
| UserPromptSubmit | User sends prompt | `promptsubmit/phases/` |
| PreToolUse | Before tool calls | `pretool/phases/` |
| PostToolUse | After tool calls | `posttool/phases/` |
| SubagentStart | Subagent starts | `subagent_start/` |

## Notable PreToolUse Validators

| Phase | Behavior |
|-------|----------|
| `planning_schema_validator` | Blocks invalid CriterionV2 in `*-plan.yaml` / `*-spec.yaml` |
| `epic_decompose_validator` | Validates spec directory structure (YAML-only, no markdown) |

Phase execution order: `hooks/pretool/runner.py` PHASES list. First block wins.

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `PROJECT_ROOT` | For tests | Database path resolution |

## Common Gotchas

1. **Hook not firing**: Check `~/.claude/settings.json` not `~/.claude.json`
2. **Import errors**: Ensure `PROJECT_ROOT` is set for tests
3. **Permission denied**: Make hook scripts executable (`chmod +x`)

## Intentional Patterns

- **Dual imports**: Try/except for both direct execution and module invocation
- **Exclusive transactions**: `DatabaseConnection(db_path, exclusive=True)` for race conditions
- **Boolean env vars**: Accept `true`, `1`, `yes` (case-insensitive)
- **CLI context decorators**: Use `@with_db_path` or `@with_repository` from `formaltask.cli.context` for db_path/repo initialization in CLI commands

## Error Handling Style Guide

### Required: All handlers have visibility

```python
# BAD: Silent swallowing
except ValueError:
    pass

# GOOD: Minimum DEBUG log
except ValueError as e:
    logger.debug("Parse failed, using fallback: %s", e)
```

### Exception Levels

| Level | When | Example |
|-------|------|---------|
| `ERROR` | Data loss risk, user action needed | Database write failed |
| `WARNING` | Degraded but recoverable | API retry after timeout |
| `DEBUG` | Expected fallback paths | JSON parse → markdown extraction |

### Patterns by Context

| Context | Pattern |
|---------|---------|
| **Database ops** | ROLLBACK + re-raise |
| **Import fallbacks** | `except ModuleNotFoundError:` with fallback import |
| **TUI widgets** | `except NoMatches:` + comment explaining expected state |
| **File operations** | Log path + error, return default |
| **Parsing** | Log input context, try next strategy |

### Anti-Patterns

```python
# Anti-pattern: Bare Exception without logging
except Exception:
    pass

# Anti-pattern: Swallowing without context
except OSError:
    return None

# Anti-pattern: Over-broad catch hiding bugs
except Exception as e:
    return default  # Hides TypeError, AttributeError, etc.
```
