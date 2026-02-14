# Architecture Overview

FormalTask is a Python CLI that orchestrates parallel AI coding agents through a structured task lifecycle.

## System diagram

```
+-------------------------------------------------------+
|                    ft CLI (pm.py)                      |
|  +------+ +------+ +------+ +--------+ +---------+   |
|  | task | | epic | | work | | review | | formula |   |
|  +--+---+ +--+---+ +--+---+ +---+----+ +----+----+   |
+-----+--------+--------+---------+------------+--------+
      |        |        |         |            |
      v        v        v         v            v
+-------------------------------------------------------+
|              formaltask/ (core package)                |
|                                                       |
|  tasks/          Task lifecycle, dependencies, guards |
|  workers/        Worker spawning, monitoring, resume  |
|  db/             SQLite operations, migrations        |
|  validators/     PreToolUse validators (TDD, etc.)    |
|  epics/          Epic management, spec parsing        |
|  apps/           TUI dashboard, browse interface      |
+-------------------------+-----------------------------+
                          |
                          v
+-------------------------------------------------------+
|           .claude/formaltask.db (SQLite)               |
|                                                       |
|  epics, tasks, acceptance_criteria, commits,          |
|  task_reviews, task_dependencies, learnings           |
+-------------------------------------------------------+
```

## Key concepts

### Task lifecycle

```
open -> in_progress -> pending_merge -> completed
  |         |  |  |
  |         |  |  +-> pending_review -> completed / in_progress
  |         |  +----> blocked_user   -> in_progress (human answers)
  |         |  +----> blocked        -> in_progress / deferred
  |         +-------> completed
  |         +-------> cancelled
  +-> deferred -> open
```

9 states. `pending_review` and `blocked_user` are IPC states (worker signals human). `pending_merge` waits for PR merge. All non-terminal states can reach `cancelled`. Quality gates enforce reviews and acceptance criteria before completion.

### Workers and worktrees

Each worker runs in an isolated git worktree:

```
project/                     # Main repo (master)
+-- .worktrees/
    +-- task-42/             # Worktree for task #42
    +-- task-43/             # Worktree for task #43
```

Workers are Claude Code sessions running in tmux. FormalTask:

1. Creates a branch (`task-42`) and worktree
2. Starts a tmux session (`task-42`)
3. Injects the task assignment, quality standards, and completion workflow
4. The worker codes, reviews, tests, and calls `ft task complete`

### Dependency chains

Tasks can declare dependencies:

```bash
ft task update 3 --depends-on 1 --depends-on 2
```

`ft work spawn --epic my-epic` respects these -- task #3 won't spawn until #1 and #2 are complete.

### Hook system

FormalTask uses Claude Code hooks for real-time enforcement:

| Hook | Directory | Purpose |
| --- | --- | --- |
| **PreToolUse** | `hooks/pretool/` | Block dangerous operations (SQL injection, file guard, TDD enforcement) |
| **PostToolUse** | `hooks/posttool/` | Track tool usage, inject context, skill span logging |
| **SessionStart** | `hooks/session_start/` | Load task context, delta handoff injection |
| **SessionEnd** | `hooks/session_end/` | Complete skill spans, clean up |
| **SubagentStop** | `hooks/stop/` | Enforce task completion before subagent exits |
| **SubagentStart** | `hooks/subagent_start/` | Inject review-store instructions |

Hooks live in `hooks/` and are registered in `~/.claude/settings.json`.

### Quality gates

Before a task can complete (`ft task complete`), it must pass:

1. **Commit evidence** — at least one commit linked to the task
2. **Reviews** — configurable per-task via `metadata.required_reviews` (default: `code-quality`). Reviews are append-only (round auto-increments, old rounds preserved). P0/P1 findings block unless dispositioned (`wontfix`/`fixed`/`needshuman`).
3. **Review freshness** — `reviewed_sha` must match HEAD for code files (`.py`, `.ts`, `.js`, `.sql`, `.sh`). Non-code changes don't trigger staleness.
4. **Acceptance criteria** — optional runnable commands with 300s timeout

Tasks can define custom `completion_rules` in metadata that prepend before builtin rules (first-match-wins). This enables escalation policies like round caps.

### Formulas

Reusable YAML templates for generating parameterized epic structures. See [Formula System](formulas.md).

### Worktree architecture

How git worktrees, symlinks, and merge protection work together. See [Worktree Architecture](worktrees.md).

### Rules kernel

Unified condition evaluation engine for completion gating, tool redirection, and worker templates. See [Rules Kernel](rules-kernel.md).

### Delta handoff

Context preservation across conversation compaction. See [Delta Handoff](delta-handoff.md).

## Package structure

```
formaltask/
+-- cli/
|   +-- pm.py              # Entry point, argument parsing
|   +-- commands/           # Noun modules (task, epic, work, review, formula)
|   |   +-- task.py         # Routes to verb modules (task_add, task_list, etc.)
|   |   +-- task_add.py     # Individual verb implementation
|   |   +-- ...
|   +-- base.py             # CLIError, exit codes
|   +-- context.py          # Decorators (@with_repository, @with_db_path)
|   +-- output.py           # JSON/stream output formatting
+-- db/
|   +-- connection.py       # DatabaseConnection (context manager)
|   +-- path.py             # Database path resolution
|   +-- migrations.py       # Schema migration runner
+-- tasks/
|   +-- lifecycle.py        # State transitions
|   +-- dependencies.py     # Dependency graph resolution
|   +-- guards.py           # Completion guards (review, criteria)
+-- workers/
|   +-- spawner.py          # Create worktree + tmux session
|   +-- monitor.py          # Health checking, status
|   +-- templates/          # Jinja2 templates for worker instructions
+-- validators/
    +-- tdd_guard.py        # Enforce test-first development
    +-- doc_guard.py        # Enforce documentation updates
    +-- ...
```

## Database

SQLite with WAL mode. Schema: `formaltask/data/schema.sql`. Migrations: `formaltask/db/migrations/`.

Key tables:

| Table | Purpose |
| --- | --- |
| `epics` | Epic metadata (name, description, status) |
| `tasks` | Task records with status, timestamps, metadata. Dependencies stored as `depends_on` JSON column. Learnings stored in `metadata` JSON. |
| `acceptance_criteria` | Per-task criteria with optional runnable `command` |
| `task_reviews` | Review records with severity, findings, round, reviewed_sha. PK: `(task_id, review_type, round)` |
| `finding_dispositions` | Per-finding disposition (wontfix/fixed/needshuman). PK: `(task_id, file, line)` |
| `commits` | Git commits linked to tasks |
| `work_sessions` | Worktree-to-task mapping |
| `plan_documents` | Planning documents linked to epics |
| `planning_state` | Planning workflow state per project |
| `schema_migrations` | Applied migration tracking |

## Extending FormalTask

### Adding a CLI command

1. Create `formaltask/cli/commands/my_command.py` with `COMMAND_NAME`, `COMMAND_HELP`, `setup_parser()`, `execute()`
2. The plugin discovery system finds it automatically

### Adding a verb to an existing noun

1. Create the verb module (e.g., `formaltask/cli/commands/task_archive.py`) with `setup_parser()` and `execute()`
2. Add the verb to the noun module's `_VERBS` dict

### Adding a hook

1. Create a phase in `hooks/<event>/phases/my_phase.py` with a `check(ctx)` function
2. Register it in the runner's `PHASES` list
