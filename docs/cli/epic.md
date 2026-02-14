# ft epic

Manage epics (create, list, close, decompose, health, review, update)

## epic close

```
ft epic close [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `epic_name` | Name of the epic to archive **(required)** | - |
| `--force` | Archive even with incomplete tasks | `False` |
| `--db-path` | Path to database (default: auto-detect) | - |
| `--projects-dir` | Projects directory (default: ~/projects) | `~/projects` |

## epic create

```
ft epic create [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `epic_name` | Epic name (kebab-case recommended) **(required)** | - |
| `description` | Epic description **(required)** | - |
| `--skip-review` | Skip review phase | `False` |
| `--db-path` | Path to database (default: auto-detect) | - |

## epic decompose

```
ft epic decompose [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `epic_name` | Epic name **(required)** | - |
| `spec_dir` | Path to spec directory containing task-*.yaml files **(required)** | - |
| `--db-path` | Path to database (default: auto-detect) | - |
| `--force` | Delete existing tasks and re-decompose (GitHub issues NOT deleted) | `False` |
| `--validate` | Validate existing tasks only (don't create new tasks) | `False` |

## epic health

```
ft epic health [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `epic_name` | Epic to validate **(required)** | - |
| `--db-path` | Database path | - |

## epic list

```
ft epic list [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `--archived` | Include archived epics | `False` |
| `--names` | Output only epic names, one per line (for scripting) | `False` |
| `--db-path` | Path to database (default: auto-detect) | - |

## epic review

```
ft epic review [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `epic_name` | Epic name **(required)** | - |
| `--db-path` | Path to database (default: auto-detect) | - |
