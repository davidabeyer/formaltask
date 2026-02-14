# Utility Commands

Standalone commands that don't require a noun prefix.

## ft commit-link

Manually link a commit to a task

```
ft commit-link [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `task_id` | Task ID to link to **(required)** | - |
| `commit_hash` | Git commit hash **(required)** | - |
| `--message` | Custom commit message (uses git message if not provided) | - |
| `--repo-path` | Path to git repository (defaults to current directory) | - |
| `--db-path` | Database path (default: auto-detect) | - |

## ft commit-scan

Scan git commits and link to tasks

```
ft commit-scan [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `--task-id` | Only scan for specific task ID | - |
| `--since` | Only scan commits since date (ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ) | - |
| `--repo-path` | Path to git repository (defaults to current directory) | - |
| `--db-path` | Database path (default: auto-detect) | - |

## ft doctor

Check formaltask health

```
ft doctor [options]
```

## ft learning

Capture a learning (optionally target siblings with --for)

```
ft learning [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `learning` | Learning to capture (max 200 chars) **(required)** | - |
| `--for` | Target sibling task IDs (comma-separated). Omit to capture for self. | - |
| `--db-path` | Database path (default: auto-detect) | - |

## ft setup

Interactive setup wizard for formaltask

```
ft setup [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `--yes` / `-y` | Auto-confirm all prompts (non-interactive mode) | `False` |
| `--db-path` | Database path (default: .claude/formaltask.db) | - |

## ft skill-init

Initialize skill run with DB registration and output directories

```
ft skill-init [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `stage` | Stage name (e.g., critique-specs, plan-decompose) **(required)** | - |
| `project` | Project name or path (optional, auto-detects if omitted) | - |
| `--skill` | Skill name for SkillRun (defaults to stage name) | - |
| `--title` | Title for SkillRun (defaults to '{skill} {project} Round {N}') | - |
| `--db-path` | Path to database (default: auto-detect) | - |
