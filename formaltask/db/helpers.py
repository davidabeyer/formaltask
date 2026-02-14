"""Database helper utilities for common patterns.

This module provides reusable helpers for:
- Task validation with ensure_task_exists()
- Atomic transactions with transaction() context manager
"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from typing import Any

from formaltask.exceptions import TaskNotFoundError

logger = logging.getLogger(__name__)

__all__: list[str] = [
    "ensure_task_exists",
    "parse_depends_on",
    "transaction",
]


def parse_depends_on(depends_on_json: str | list | None) -> list[int]:
    """Parse depends_on JSON string to list of task IDs.

    Safely parses JSON array strings from database, returning empty list
    for None, empty string, invalid JSON, or non-list JSON values.
    Non-integer elements are filtered out to maintain type safety.

    Args:
        depends_on_json: JSON string containing array of task IDs, already-parsed
            list, or None.

    Returns:
        List of integer task IDs, or empty list if input is invalid.
    """
    if not depends_on_json:
        return []
    # Handle already-parsed list (SQLite JSON extension may return native list)
    if isinstance(depends_on_json, list):
        return [x for x in depends_on_json if isinstance(x, int)]
    try:
        result = json.loads(depends_on_json)
        if not isinstance(result, list):
            logger.warning("malformed depends_on JSON: not a list")
            return []
        # Filter to only integers for type safety (task IDs are always int)
        return [x for x in result if isinstance(x, int)]
    except json.JSONDecodeError:
        logger.warning("malformed depends_on JSON: %s", depends_on_json[:50])
        return []


def ensure_task_exists(cursor, task_id: int) -> dict[str, Any]:
    """Validate task exists and return row as dict.

    Args:
        cursor: Database cursor (connection must have row_factory=sqlite3.Row)
        task_id: Task ID to validate

    Returns:
        Task row as dictionary

    Raises:
        TaskNotFoundError: If task doesn't exist

    Note:
        Requires cursor from connection with row_factory=sqlite3.Row set.
    """
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        raise TaskNotFoundError(task_id)
    return dict(row)


@contextmanager
def transaction(connection):
    """Context manager for atomic database operations.

    Starts a transaction with BEGIN, yields the connection for use in the
    with block. Commits on normal exit, rolls back and re-raises on exception.

    Works with connections in autocommit mode (isolation_level=None) by
    explicitly issuing BEGIN.

    Args:
        connection: Database connection

    Yields:
        The connection for executing queries within the transaction
    """
    cursor = connection.cursor()
    cursor.execute("BEGIN")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
