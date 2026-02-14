# CLI Reference

FormalTask uses a noun-verb CLI pattern:

```bash
ft <noun> <verb> [args] [flags]
```

## Nouns

| Noun | Purpose | Verbs |
| --- | --- | --- |
| [`task`](task.md) | Manage tasks | `add`, `list`, `show`, `update`, `complete`, `cancel`, `defer`, `create-from-finding` |
| [`epic`](epic.md) | Manage epics | `create`, `list`, `close`, `decompose`, `health`, `review` |
| [`work`](work.md) | Manage workers | `spawn`, `list`, `watch`, `inbox`, `dashboard`, `resume`, `restart`, `blocked` |
| [`review`](review.md) | Manage reviews | `store`, `disposition` |
| [`formula`](formula.md) | Manage templates | `list`, `cook`, `batch` |

## Global flags

Flags go **before** the noun:

```bash
ft --json task list my-epic      # JSON output
ft --dry-run task complete 1     # Preview without executing
ft --preflight task complete 1   # Validate without executing
```

| Flag | Effect |
| --- | --- |
| `--json` | Machine-readable JSON output |
| `--stream` | Stream output progressively |
| `--preflight` | Validate prerequisites without executing |
| `--dry-run` | Show what would happen without doing it |

## Standalone utilities

These don't use a noun prefix:

| Command | Purpose |
| --- | --- |
| `ft setup` | Interactive setup wizard |
| `ft doctor` | Check FormalTask health and dependencies |
| `ft learning` | Capture a learning for knowledge sharing |
| `ft commit-link` | Manually link a git commit to a task |
| `ft commit-scan` | Scan git history and auto-link commits |
| `ft skill-init` | Initialize a skill run |

See [Utilities](utilities.md) for full details.

## Common workflows

### Start a new project

```bash
ft setup
ft epic create my-feature
ft task add my-feature "First task" "Description" --criteria "It works"
```

### Run parallel workers

```bash
ft work spawn --epic my-feature   # Spawn all ready tasks
ft work watch                     # Monitor and auto-spawn
ft work inbox                     # Check for blocked workers
```

### Complete a task manually

```bash
ft task complete 42               # Runs quality gates
ft task complete 42 --no-evidence # Skip commit evidence guard (audit/doc tasks)
```

### Check epic health

```bash
ft epic list                      # List all epics
ft epic health my-feature         # Check for dependency issues
ft epic review my-feature         # Run code review across all tasks
```
