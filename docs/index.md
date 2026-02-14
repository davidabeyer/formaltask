# FormalTask

Structured task management for AI-assisted development workflows.

FormalTask (`ft`) orchestrates parallel AI coding agents through a database-backed task lifecycle. You define epics and tasks, FormalTask spawns isolated workers in git worktrees, enforces quality gates (reviews, tests, acceptance criteria), and tracks everything in SQLite.

## Who is this for?

- **Solo developers** using Claude Code who want structured task tracking with automatic quality enforcement
- **Teams** running multiple AI agents in parallel on the same codebase

## 30-Second Quickstart

```bash
pip install formaltask
ft setup                         # Interactive setup wizard
ft epic create my-feature        # Create an epic
ft task add my-feature "Add auth endpoint" "JWT-based authentication" \
    --criteria "POST /auth/login returns 200 with valid credentials"
ft work spawn 1                  # Spawn a worker for task #1
ft work watch                    # Monitor workers
```

## How it works

```
Epic (goal) → Tasks (units of work) → Workers (AI agents in worktrees)
                                           |
                                    Code → Review → Tests → Complete
```

1. **Epics** group related work. Each epic gets decomposed into tasks.
2. **Tasks** have acceptance criteria, dependency chains, and status tracking.
3. **Workers** are Claude Code sessions running in isolated git worktrees. Each worker gets a task assignment, quality gates, and completion workflow.
4. **Quality gates** enforce reviews, test passage, and acceptance criteria before a task can be marked complete.

## CLI Design

FormalTask uses a noun-verb CLI pattern (like `gh` or `kubectl`):

```bash
ft <noun> <verb> [args]

ft task list my-epic          # List tasks in an epic
ft work spawn --epic my-epic  # Spawn workers for all ready tasks
ft epic health my-epic        # Check epic for dependency issues
```

Five nouns: `task`, `epic`, `work`, `review`, `formula`. Plus standalone utilities: `setup`, `doctor`, `learning`.

## Next steps

- [Quickstart Guide](getting-started/quickstart.md) - Full walkthrough from install to first completed task
- [CLI Reference](cli/index.md) - Complete command reference
- [Planning Workflow](../skills/PLANNING-WORKFLOW.md) - Plan → critique → revise → decompose lifecycle
- [Architecture Overview](architecture/overview.md) - How FormalTask works under the hood
