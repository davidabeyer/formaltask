# formaltask/db/

Database connection and path resolution for FormalTask.

## Quick Start

```python
from formaltask.db.connection import DatabaseConnection
from formaltask.db.path import get_db_path

# Get canonical database path
db_path = get_db_path()

# Read operations
with DatabaseConnection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (42,))

# Atomic write operations
with DatabaseConnection(db_path, exclusive=True) as conn:
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", ("completed", 42))
    # Auto-commits on success, rollbacks on exception
```

## DatabaseConnection

Context manager providing SQLite connections with production defaults.

### Features

| Feature | Default | Purpose |
|---------|---------|---------|
| WAL mode | Enabled | Concurrent reads during writes |
| busy_timeout | 5000ms | Wait for locks instead of failing |
| Foreign keys | ON | Enforce referential integrity |
| Row factory | sqlite3.Row | Dict-like row access |

### Exclusive Mode

Use `exclusive=True` for multi-step atomic operations:

```python
# Race-safe status transition
with DatabaseConnection(db_path, exclusive=True) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    current = cursor.fetchone()["status"]
    if current == "open":
        cursor.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
    # Commits automatically on exit
```

### WAL Skip

WAL mode is automatically disabled for:
- `/tmp/` paths (test databases)
- Paths containing "pytest" (test isolation)

## Path Resolution

`get_db_path()` finds `formaltask.db` with security checks.

### Resolution Order

1. `PROJECT_ROOT/.claude/formaltask.db` (if `PROJECT_ROOT` env set)
2. `.task/project_root` or `.task/main_repo` pointer (worktree)
3. `cwd/.claude/formaltask.db` (fallback)

### Security

- **Symlinks rejected** — Prevents symlink attacks on `.claude/` and `formaltask.db`
- **Home directory blocked** — Refuses `~/.claude/formaltask.db` (wrong location for project)
- **System dirs blocked** — `/dev`, `/proc`, `/sys`, `/etc`, `/var`, `/boot`, `/root`

### User Path Validation

For `--db-path` CLI argument:

```python
from formaltask.db.path import validate_user_db_path

path = validate_user_db_path("/custom/path/formaltask.db")
# Checks: .db extension, not symlink, not system dir, exists
```

## Key Files

| File | Purpose |
|------|---------|
| `connection.py` | DatabaseConnection context manager |
| `path.py` | `get_db_path()`, `validate_user_db_path()` |
| `helpers.py` | `ensure_task_exists()`, query utilities |
| `schema.py` | Schema creation and migrations |

## Common Gotchas

| Issue | Solution |
|-------|----------|
| "Database not found" | Check `PROJECT_ROOT` or run from project dir |
| "Symlink not allowed" | Use real paths, not symlinks |
| Lock timeout | Another process has exclusive lock — wait or check for hung workers |
| WAL files (.db-wal, .db-shm) | Normal for WAL mode — don't delete while db is open |

## See Also

- `formaltask/tasks/` — Task CRUD using DatabaseConnection
- `formaltask/core/` — Completion checking
