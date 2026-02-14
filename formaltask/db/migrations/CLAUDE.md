# migrations/ CLAUDE.md

Migrations are self-contained time capsules. Each migration defines its own helpers.

## column_exists Pattern

```python
def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Check if column exists in table."""
    valid_tables = {"tasks", "epics"}  # ← ONLY tables THIS migration touches
    if table not in valid_tables:
        raise ValueError(f"Invalid table name: {table}")
    cursor.execute(f"PRAGMA table_info({table})")  # nosemgrep: ...
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns
```

## DO NOT

- Import column_exists from helpers.py (breaks isolation)
- Use superset allowlists from other migrations
- Modify old migrations for style consistency

## Template

Follow the `column_exists` pattern above for new migrations.
