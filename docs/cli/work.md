# ft work

Manage parallel workers (spawn, list, inbox, watch, dashboard, resume, restart, blocked)

## work blocked

```
ft work blocked [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `question` | Question or context for why you're blocked **(required)** | - |
| `--db-path` | Database path (default: auto-detect) | - |

## work dashboard

```
ft work dashboard [options]
```

## work inbox

```
ft work inbox [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `--json` | Output as JSON (for supervisor skill) | `False` |
| `--db-path` | Database path (default: auto-detect) | - |

## work list

```
ft work list [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `--db-path` | Database path | - |
| `--why` | Show why a specific task is blocked | - |
| `--complete` | Show completion blockers (use with --why) | `False` |

## work restart

```
ft work restart [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `--db-path` | Database path | - |
| `--dry-run` | Show what would restart without doing it | `False` |
| `--resume` | Resume Claude sessions with --continue (keeps context) | `False` |

## work resume

```
ft work resume [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `task_ids` | Task IDs to resume (mutually exclusive with --epic) | - |
| `--epic` | Resume all in_progress tasks in the epic | - |
| `--db-path` | Database path (default: auto-detect) | - |
| `-m` / `--message` | Message to inject into resumed Claude session | `Continue working on the task.` |

## work spawn

```
ft work spawn [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `task_ids` | Task IDs to spawn (optional if --epic is used) **(required)** | - |
| `--epic` | Spawn all dependency-ready tasks in the epic | - |
| `--db-path` | Database path (default: auto-detect) | - |
| `--fresh` | Delete existing worktree/branch before recreation for clean start | `False` |
| `--no-worker` | Mark task in_progress without spawning tmux session (replaces task-start) | `False` |

## work watch

```
ft work watch [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `--db-path` | Database path | - |
| `--spawn` / `-s` | Auto-spawn ready tasks (use -n to set max workers, default: 5) | `False` |
| `--max-workers` / `-n` | Max concurrent workers [default: 5] | `5` |
| `--cleanup` | Kill orphaned sessions (completed tasks with merged PRs) | `False` |
| `--interval` | Polling interval [default: 10s] | `10` |
| `--log-file` | Log file path | `~/.claude/logs/watch.log` |
