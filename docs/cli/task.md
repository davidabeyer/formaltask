# ft task

Manage tasks (add, list, show, update, complete, cancel, defer)

## task add

```
ft task add [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `epic_name` | Epic to add task to **(required)** | - |
| `title` | Task title **(required)** | - |
| `description` | Task description **(required)** | - |
| `--criteria` | Acceptance criteria (use multiple --criteria flags) **(required)** | - |
| `--depends-on` | Task ID this task depends on (use multiple --depends-on flags) | - |
| `--db-path` | Path to database (default: auto-detect) | - |
| `--metadata` | JSON metadata including artifact_type and artifact_content | - |
| `--status` | Initial task status (default: open, use blocked for critique-first workflow) (choices: open, blocked) | `open` |
| `--template` / `-t` | Task template name (default: implementation) | `implementation` |
| `--spec-review` | Use spec-review template (shortcut for --template spec-review) | `False` |
| `--epic-review` | Use epic-review template (shortcut for --template epic-review) | `False` |

## task cancel

```
ft task cancel [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `task_id` | Task ID(s) to cancel (comma-separated for bulk cancel) **(required)** | - |
| `--reason` | Cancellation reason (min 20 characters) **(required)** | - |
| `--force-terminal` | Allow cancelling tasks in terminal states (completed/cancelled) for data repair | `False` |
| `--db-path` | Database path (default: auto-detect) | - |

## task complete

```
ft task complete [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `task_id` | Task ID to complete **(required)** | - |
| `--db-path` | Database path (default: auto-detect) | - |
| `--no-evidence` | Skip evidence guard for audit/doc tasks without code changes | `False` |
| `--completion-evidence` | Evidence that work was already done. Sets completion_evidence field. | - |

## task create-from-finding

```
ft task create-from-finding [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `file` | Source file path containing the finding **(required)** | - |
| `line` | Line number of the finding **(required)** | - |
| `--title` | Title for the new task **(required)** | - |
| `--task-type` | Task workflow type (default: critique-gated) | `critique-gated` |
| `--epic` | Epic name (auto-detected from .task/id if in worker context) | - |
| `--spawn` | Immediately spawn a worker for the created task | `False` |
| `--db-path` | Database path (default: auto-detect) | - |

## task defer

```
ft task defer [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `task_id` | Task ID to defer **(required)** | - |
| `--reason` | Reason for deferring (>= 20 characters required) **(required)** | - |
| `--db-path` | Database path (default: auto-detect) | - |

## task list

```
ft task list [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `epic_name` | Epic name **(required)** | - |
| `--status` | Filter by status (choices: open, in_progress, completed) | - |
| `--search` / `-s` | Filter tasks by title or description (case-insensitive) | - |
| `--db-path` | Database path (default: auto-detect) | - |

## task show

```
ft task show [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `task_id` | Task ID to show **(required)** | - |
| `--deps` | Show dependency tree | `False` |
| `--db-path` | Path to database | - |

## task update

```
ft task update [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `task_id` | Task ID to update **(required)** | - |
| `--title` | New title for the task | - |
| `--description` | New description for the task | - |
| `--add-criteria` | Add acceptance criterion text | - |
| `--remove-criteria` | Remove acceptance criterion by index (0-based) | - |
| `--reset-status` | Reset status from in_progress to open (orphan recovery) | `False` |
| `--metadata` | JSON to merge into task metadata (e.g., '{"critique_count": 1}') | - |
| `--depends-on` | Task ID this task depends on (can be used multiple times) | - |
| `--clear-deps` | Remove all dependencies (sets depends_on to []) | `False` |
| `--db-path` | Database path (default: auto-detect) | - |
