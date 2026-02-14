# FormalTask Project

## Tech Stack

- Python 3.11, pytest, BATS
- SQLite 3 — **Database: `PROJECT_ROOT/.claude/formaltask.db`** (NOT `~/.claude/`)
- MCP servers, Git hooks, TDD Guard
- tmux 3.2+ (for `-e` flag to pass TASK_ID env var to workers; older versions use worktree path fallback)

## Project Structure

```
formaltask/              # Repository root
├── formaltask/         # Core package
│   ├── cli/            # CLI commands (ft <command>)
│   ├── core/           # Completion checking, config, rules engine
│   ├── db/             # Database connection, migrations
│   ├── epics/          # Epic CRUD, YAML parsing
│   ├── git/            # Worktree management, PR queries
│   ├── llm/            # LLM integration (OpenRouter)
│   ├── review/         # Review context, prompt building
│   ├── state/          # Findings, session tracking
│   ├── tasks/          # Task lifecycle, dependencies, guards
│   ├── validators/     # PreToolUse validators (TDD, doc-guard, etc.)
│   ├── vault/          # Knowledge storage
│   ├── workers/        # Worker spawning, monitoring, resume
│   ├── apps/           # TUI applications (dashboard, browse)
│   └── utils/          # Shared utilities
├── agents/             # Subagent definitions
├── hooks/              # Hook entry points (see hooks/CLAUDE.md)
│   ├── pretool/        # PreToolUse hooks (call formaltask.validators)
│   ├── posttool/       # PostToolUse hooks
│   ├── session_start/  # SessionStart hooks
│   ├── session_end/    # SessionEnd hooks
│   ├── promptsubmit/   # UserPromptSubmit hooks
│   └── tests/          # Hook-specific tests
├── tests/              # Main pytest test suite
├── .githooks/          # Tracked git hooks (see .githooks/README.md)
└── .claude/
    ├── commands/       # Slash commands
    ├── skills/         # Custom skills
    └── tdd-guard/      # TDD enforcement
```

## Agent Files (CLAUDE.md, skills/, agents/, commands/)

**Every line earns its place.** These files are agent context—not documentation.

- Direct instructions, not explanations
- Examples over prose
- Antirez rules apply here too: flat > nested, obvious > clever. If a cold reader can't understand the instruction on first read, rewrite it.
- Delete filler words, hedging, redundancy
- If it doesn't change agent behavior, cut it

## Setup (New Clones)

```bash
git config core.hooksPath .githooks
```

Enables pre-commit, pre-push, pre-merge-commit hooks. Worktrees get `.githooks` symlinked automatically.

**Python Version**: `.python-version` → pyenv → Python 3.11 (prevents pytest-mock failures).

## Common Commands

```bash
# Tests
pytest tests/ --cov=formaltask

# Git & Linting
ruff check formaltask/ --fix && ruff format formaltask/

# FormalTask CLI
ft <noun> <verb> [args]
ft task complete 42
ft task list my-epic
```

## Worker CLI (EXACT FLAGS - NO OTHERS EXIST)

**Spawn takes 10-30 seconds.** Don't reset or cancel.

```bash
ft work spawn <id>                          # NOT worker-spawn, NOT task-start
ft task complete <id>                       # NO --comment flag exists!
ft task complete <id> --skip-review
ft task complete <id> --create-pr
ft task cancel <id> [--force]
tmux kill-session -t task-<id>
ft review disposition FILE LINE --reason "R"  # wontfix (--needshuman to escalate)
ft work inbox                              # View blocked workers awaiting input
ft task create-from-finding FILE LINE --title "T"  # New critique-gated task from finding
```

## Project Commands

```bash
# Reviews
/review epic:auth-system
/review list epic:name --status open
/review-fix epic --dry-run

# Tasks
/task-add my-epic               # Interactive
/task-add my-epic "Title"       # With title

# Worker Coordination
/inbox                             # View/respond to pending worker questions
```

## FormalTask Workflow

**Interactive:** `ft work spawn <id>` → work → `ft task complete <id>`

**Parallel:** `ft work spawn --epic <epic>` spawns tmux workers

| Action | Command |
|--------|---------|
| List spawnable | `ft work list` |
| Spawn all ready | `ft work spawn --epic <epic>` |
| Spawn single | `ft work spawn <id>` |
| Complete task | `ft task complete <id>` |
| Show task | `ft task show <id>` |
| List epics | `ft epic list` |
| Check blocked workers | `ft work inbox` |

**Chaining:** `.task/chain` signal → spawns dependent tasks from completed task's branch (not master). Multi-dep tasks need all PRs merged first.

**MUST NOT:** Skip FormalTask workflow (Plan → Specs → Epic → Tasks). Use placeholder dates — run `date -u +"%Y-%m-%dT%H:%M:%SZ"`.

## Invocation: Skills vs Commands vs ft CLI

Three ways to invoke FormalTask functionality. Use the right one:

| Layer | Invoke via | Use when | Examples |
|-------|-----------|----------|----------|
| **Skills** | `/plan`, `/critique`, `/decompose` | Complex multi-step workflows with subagents | Planning, code review, auditing |
| **Commands** | `/inbox`, `/review` | Quick actions, thin CLI wrappers | View inbox, store review |
| **ft CLI** | `ft task complete`, `ft work spawn` | Direct operations, scripting | Task CRUD, worker control, epic management |

**Planning lifecycle** (skills): `/plan` → `/critique` → `/revise` → `/decompose` → `ft epic decompose` → `ft work spawn`. See [Planning Workflow](skills/PLANNING-WORKFLOW.md).

## Agent Requirements

All custom agents MUST include `mcp__auggie-mcp__codebase-retrieval` and `mcp__morph-mcp__warpgrep_codebase_search`.

## Testing Gotchas

### Monkeypatching
```python
# BAD — direct import bypasses patches
from module import function
monkeypatch.setattr("module.function", mock)  # Never seen

# GOOD — import module, access attribute
import module as m
monkeypatch.setattr(m, "function", mock)  # Works
```

### Threading Barrier
```python
# BAD — Barrier(5) with 2 operations = deadlock
barrier = threading.Barrier(num_threads)

# GOOD — Barrier matches operation count
barrier = threading.Barrier(len(operations))
```

## Common Gotchas

| Issue | Rule |
|-------|------|
| **Database location** | `PROJECT_ROOT/.claude/formaltask.db` — NOT `~/.claude/` |
| Database connection | `DatabaseConnection` from `formaltask.db.connection` — NEVER `sqlite3.connect()` |
| Worker MCP tools | Workers only have Bash/Read/Write/Edit — NO mcp__tmux__ tools |
| Exception constructors | `TaskNotFoundError(task_id)` not `TaskNotFoundError("msg")` |
| Task status | `TaskStatus.COMPLETED` not `"completed"` — strings cause silent bugs |
| CLI command signature | `execute(ctx: CLIContext, args)` with `@with_repository` — NOT `execute(db_path, args)` |
| Validator returns | `{"decision": "block", "reason": "..."}` or `None` — NOT booleans |
| Atomic state | `DatabaseConnection(db_path, exclusive=True)` for multi-step updates |
| Exit codes | `ExitCode.NOT_FOUND.value` — NOT magic numbers |
| Worktree paths | Always resolve via `PROJECT_ROOT` |
| tmux TASK_ID | tmux 3.2+ uses `-e`; older falls back to worktree path |
| Doc-guard bypass | Internal refactor, no API change? → `SKIP_DOC_GUARD=1 git commit` |
| Self-critique tasks | `task_type=critique-gated` sets `required_reviews: ["self-critique"]`; standard review gate blocks |

## Subdirectory Documentation

| Directory | Content |
|-----------|---------|
| `hooks/CLAUDE.md` | Hook entry points, event-driven workflows |
| `formaltask/db/migrations/CLAUDE.md` | Migration isolation pattern |
| `formaltask/validators/CLAUDE.md` | PreToolUse validator gotchas |
| `docs/CLAUDE.md` | Documentation style rules |

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | Yes | LLM operations (Gemini via OpenRouter) |
| `PROJECT_ROOT` | For tests and CLI | Database path resolution |
| `ANTHROPIC_API_KEY` | GitHub Actions | Doc-update workflow (repo secret) |

## GitHub Actions

### Doc-Update on PR Merge
`.github/workflows/doc-update-on-merge.yml` — auto-updates **README.md** (not CLAUDE.md) when PRs merge to main/master. Skips bot PRs and `docs:` prefixed titles. Two-agent: generator creates PR, validator verifies against source code.

Required secret: `ANTHROPIC_API_KEY`  <!-- pragma: allowlist secret -->

### Stub Check on PRs
`.github/workflows/stub-check.yml` — blocks PRs with stub functions (`pass`, `...`, `raise NotImplementedError`).

**Escape hatch:** `# STUB: reason` comment within 5 lines above the function.
**Whitelisted:** test files, `@abstractmethod`, Protocol methods.
Reuses `formaltask/validators/stub_detector.py`.

## Hook Security (hooks/**/*.py)

- **Subprocess**: Always `timeout=30` to prevent hanging
- **Git refs**: Validate no `-` prefix (argument injection)
- **Path matching**: Use `pathlib.relative_to()` not `str.startswith()` (prefix attack)
- **Exceptions**: No bare `except Exception:` - use specific types
- **JSON**: Use `formaltask.utils.read_json_from_file()` (10MB limit)
- **Env**: Use `formaltask.utils.build_subprocess_env()` (whitelist)

## Learned Patterns

*Auto-generated from session reflections. Last updated: 2026-01-23*

### Rules
- **TDD Red Phase**: Create test file before implementation to confirm initial ImportError.
- **Minimal Implementation**: Only code to pass current test; add test before new branches.
- **Schema Migration Tracking**: Populate `schema_migrations` and commit immediately after schema DDL.
- **SQLite CI Mode**: Disable WAL in CI environments, use DELETE journal mode.
- **Test Mock Paths**: When code moves between modules, update all mock paths in tests. Mocking `module_a.function` won't work if function now lives in `module_b`.
