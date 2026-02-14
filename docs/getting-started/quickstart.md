# Quickstart

Get from zero to a running AI worker in 5 minutes.

## Prerequisites

- Python 3.11+
- Git
- tmux 3.2+ (for parallel workers)
- [Claude Code](https://claude.ai/claude-code) CLI — required for `ft work spawn` (worker spawning), optional for task management

## Install

```bash
pip install formaltask
```

Verify:

```bash
ft doctor    # Checks all dependencies and config
```

## Setup

```bash
ft setup
```

This creates `.claude/formaltask.db` in your project root and configures git hooks.

## Create an epic

An epic is a container for related tasks:

```bash
ft epic create auth-system
```

## Add tasks

```bash
ft task add auth-system "Add login endpoint" \
    "JWT-based POST /auth/login endpoint" \
    --criteria "Returns 200 with valid credentials" \
    --criteria "Returns 401 with invalid credentials" \
    --criteria "Sets httpOnly cookie with JWT token"

ft task add auth-system "Add logout endpoint" \
    "Clear JWT cookie on POST /auth/logout" \
    --criteria "Returns 200 and clears auth cookie"
```

Check your tasks:

```bash
ft task list auth-system
```

## Spawn a worker

A worker is a Claude Code session running in an isolated git worktree:

```bash
ft work spawn 1    # Spawn worker for task #1
```

This creates a worktree branch, starts a tmux session, and injects the task assignment into the Claude Code session.

## Monitor workers

```bash
ft work watch              # Live monitoring, auto-spawns ready tasks
ft work list               # Quick status check
ft work inbox              # See workers waiting for human input
```

## Complete a task

Workers call `ft task complete <id>` themselves. If you're working interactively:

```bash
ft task complete 1
```

This runs quality gates (review, acceptance criteria) and marks the task complete.

## Spawn all ready tasks at once

```bash
ft work spawn --epic auth-system
```

FormalTask respects dependency chains -- it only spawns tasks whose dependencies are complete.

## What's next

- [CLI Reference](../cli/index.md) - Full command documentation
- [Architecture Overview](../architecture/overview.md) - How the pieces fit together
