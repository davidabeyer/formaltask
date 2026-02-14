# formaltask/cli/

Command-line interface for FormalTask. Entry point: `ft <command>`.

## Quick Start

```bash
# Task management
ft task-list my-epic
ft task-show 42
ft spawn 42
ft task-complete 42

# Epic management
ft epic-list
ft epic-create "My Epic"
ft epic-decompose my-epic

# Worker coordination
ft spawnable
ft blocked
ft dashboard
```

## Command Pattern

All commands follow this structure:

```python
# formaltask/cli/commands/my_command.py

from formaltask.cli.context import CLIContext, with_repository

def setup_parser(subparsers) -> None:
    """Register command with argparse."""
    parser = subparsers.add_parser("my-command", help="Brief description")
    parser.add_argument("task_id", type=int)
    parser.set_defaults(func=execute)

@with_repository
def execute(ctx: CLIContext, args) -> int:
    """Execute command. Returns exit code."""
    # ctx.db_path is pre-resolved and validated
    return 0
```

### Decorators

| Decorator | Injects | Use When |
|-----------|---------|----------|
| `@with_repository` | `CLIContext` | Command needs database |
| `@with_db_path` | `db_path: str` | Legacy commands |

### CLIContext

Immutable context with validated database path:

```python
@dataclass(frozen=True, slots=True)
class CLIContext:
    db_path: str
```

## Exit Codes

POSIX-compliant codes for agent automation:

| Code | Name | Meaning |
|------|------|---------|
| 0 | SUCCESS | Command completed |
| 1 | GENERAL_ERROR | Unspecified error |
| 2 | USAGE_ERROR | Invalid arguments |
| 64 | NOT_FOUND | Resource doesn't exist |
| 65 | ALREADY_EXISTS | Duplicate creation |
| 66 | INVALID_STATE | State machine error |
| 67 | CONFLICT | Dependency conflict |
| 68 | VALIDATION_ERROR | Input validation failed |

```python
from formaltask.cli.exit_codes import ExitCode

if not task:
    return ExitCode.NOT_FOUND.value
```

## Output Formats

Commands support multiple output modes:

```bash
ft task-list my-epic           # Human-readable (default)
ft task-list my-epic --json    # JSON for scripting
ft task-list my-epic --stream  # Progressive output
```

## AgentFriendlyParser

Concise argparse errors for LLM agents: `Unknown command 'taks-list'. Did you mean: task-list?`

## Command Discovery

Commands auto-discovered from `formaltask/cli/commands/`:

```python
from formaltask.cli.commands import discover_plugins

plugins = discover_plugins()
# {'task-list': <module>, 'spawn': <module>, ...}
```

## Key Files

| File | Purpose |
|------|---------|
| `pm.py` | Main entry point, argument parsing |
| `context.py` | CLIContext, `@with_repository` decorator |
| `base.py` | CLIError exception |
| `exit_codes.py` | ExitCode enum |
| `output.py` | OutputFormatter for JSON/stream modes |
| `commands/` | Individual command modules |

## Adding a Command

1. Create `formaltask/cli/commands/my_command.py`
2. Implement `setup_parser(subparsers)` and `execute(ctx, args)`
3. Command auto-discovered by filename (underscores → hyphens)

```python
# my_command.py → ft my-command
```

## Common Gotchas

| Issue | Solution |
|-------|----------|
| "Database not found" | Run from project dir or set `PROJECT_ROOT` |
| Exit code not int | Return `ExitCode.NOT_FOUND.value` not `ExitCode.NOT_FOUND` |
| Command not found | Check filename matches command (underscores → hyphens) |
| Missing `setup_parser` | Both `setup_parser` and `execute` required for discovery |

## See Also

- `formaltask/db/` — Database connection used by commands
- `formaltask/tasks/` — Task operations called by commands
- `formaltask/workers/` — Worker spawning
