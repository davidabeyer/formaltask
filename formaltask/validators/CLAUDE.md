# validators/ CLAUDE.md

PreToolUse validation framework for Claude Code hooks.

## Gotchas

- **Return `None` to allow** - Don't return `{}`. Empty dict is not allow.
- **Exit code 2 for block** - Not exit 1. `sys.exit(2)` means block.
- **Phases vs validators** - Edit `formaltask/validators/`, not `hooks/pretool/phases/`
- **Security = fail-closed** - `db_guard`, `sql_guard` must block on ANY error
- **Non-security = fail-open** - `tdd_guard`, `stub_detector` allow on exception
- **Path security** - `db_guard` uses `abspath()` not `realpath()` (blocks symlinks intentionally)
- **First block wins** - Phase order matters in `hooks/pretool/runner.py`
- **Clear config cache in tests** - Set `dgc._config_cache = None` to avoid state leakage
- **Morph MCP duo** - `tdd` (transformer), `tdd_guard` (entry point)

## See Also

- `README.md` - Full documentation, architecture, how to add validators
