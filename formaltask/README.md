# formaltask/

Task management system for Claude Code with epic decomposition, worker orchestration, and automated code review.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           CLI (cli/)                            │
│                    ft <command> entry point                     │
└───────────────┬─────────────────────────────────────┬───────────┘
                │                                     │
    ┌───────────▼───────────┐           ┌─────────────▼─────────────┐
    │     Epics (epics/)    │           │    Workers (workers/)     │
    │  YAML parsing, plans  │           │  spawn, monitor, resume   │
    └───────────┬───────────┘           └─────────────┬─────────────┘
                │                                     │
    ┌───────────▼───────────┐           ┌─────────────▼─────────────┐
    │     Tasks (tasks/)    │◄──────────│    Review (review/)       │
    │ lifecycle, deps, guards│           │  context, prompts, rounds │
    └───────────┬───────────┘           └─────────────┬─────────────┘
                │                                     │
    ┌───────────▼───────────┐           ┌─────────────▼─────────────┐
    │      Git (git/)       │           │     State (state/)        │
    │ worktrees, PRs, status │           │ findings, sessions        │
    └───────────┬───────────┘           └─────────────┬─────────────┘
                │                                     │
                └───────────────────┬─────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │        Core (core/)           │
                    │  completion config, checking  │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │       Database (db/)          │
                    │   connection, path, helpers   │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │      Validators (validators/) │
                    │   TDD, doc-guard, security    │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │        Utils (utils/)         │
                    │  constants, JSON, subprocess  │
                    └───────────────────────────────┘
```

## Modules

| Module | Purpose | README |
|--------|---------|--------|
| **cli/** | CLI commands (`ft <command>`), argument parsing, exit codes | [cli/README.md](cli/README.md) |
| **core/** | Completion checking, config management | [core/README.md](core/README.md) |
| **db/** | Database connection, path resolution, security | [db/README.md](db/README.md) |
| **epics/** | Epic CRUD, YAML parsing, validation, planning workflow | [epics/README.md](epics/README.md) |
| **git/** | Worktree cleanup, PR queries, git utilities | [git/README.md](git/README.md) |
| **review/** | Review context, prompt building, round tracking | [review/README.md](review/README.md) |
| **state/** | Findings state, session tracking, transcript mtime | [state/README.md](state/README.md) |
| **tasks/** | Task lifecycle, dependencies, spawnability, guards | [tasks/README.md](tasks/README.md) |
| **utils/** | TaskStatus enum, JSON limits, subprocess env | [utils/README.md](utils/README.md) |
| **validators/** | PreToolUse hooks for TDD, docs, security | [validators/README.md](validators/README.md) |
| **workers/** | Worker spawning, monitoring, crash detection | [workers/README.md](workers/README.md) |

## Quick Navigation

| I want to... | Go to |
|--------------|-------|
| Add a CLI command | [cli/README.md → Adding a Command](cli/README.md#adding-a-command) |
| Understand task states | [tasks/README.md → State Machine](tasks/README.md#state-machine) |
| Parse an epic YAML | [epics/README.md → YAML Parsing](epics/README.md#yaml-parsing) |
| Check if task can complete | [core/README.md](core/README.md) |
| Spawn a worker | [workers/README.md](workers/README.md) |
| Add a validator | [validators/README.md → Adding a New Validator](validators/README.md#adding-a-new-validator) |
| Query the database | [db/README.md → DatabaseConnection](db/README.md#databaseconnection) |
| Build a review prompt | [review/README.md → Review Prompts](review/README.md#review-prompts) |

## Getting Started

```bash
# Database location
.claude/formaltask.db

# Common commands
ft epic list                    # List all epics
ft task list my-epic            # List tasks in epic
ft work spawn 42                # Spawn worker for task
ft task complete 42             # Complete a task
ft work dashboard               # Open TUI dashboard
```

For module-specific quickstarts, see individual README files.

## Cross-Module Gotchas

| Issue | Cause | Solution |
|-------|-------|----------|
| "Database not found" | Wrong `PROJECT_ROOT` or running from wrong dir | Check [db/README.md → Path Resolution](db/README.md#path-resolution) |
| Task stuck in `in_progress` | Worker crashed, orphaned tmux | [workers/README.md](workers/README.md) |
| Epic validation fails | Circular or dangling dependencies | [epics/README.md → Validation](epics/README.md#validation--analysis) |
| PR not detected | GitHub API cache (300s TTL) | [git/README.md](git/README.md) |

## See Also

- `hooks/` — Hook entry points for Claude Code events
- `apps/` — TUI applications (dashboard, browse)
- `CLAUDE.md` — Project context for Claude Code
