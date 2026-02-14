# ft review

Manage review findings (store, disposition)

## review disposition

```
ft review disposition [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `file` | File path | - |
| `line` | Line number | - |
| `--reason` | Reason for marking disposition | - |
| `--task` | Task ID | - |
| `--list` | List dispositions | `False` |
| `--clear` | Clear entry | `False` |
| `--db-path` | Database path | - |
| `--needshuman` | Needs human review (blocks task) | `False` |
| `--fixed` | Fixed in this PR | `False` |

## review store

```
ft review store [options]
```

### Arguments

| Argument | Description | Default |
| --- | --- | --- |
| `review_json` | Review JSON (reads from stdin if not provided) | - |
| `--db-path` | Database path (default: auto-detect) | - |
