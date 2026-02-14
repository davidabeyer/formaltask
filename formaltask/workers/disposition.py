"""Query interface for finding_dispositions table."""

from pathlib import Path

from formaltask.db.connection import DatabaseConnection
from formaltask.utils.constants import DispositionType


def add_wontfix_entry(
    task_id: int,
    file: str,
    line: int | None,
    reason: str,
    db_path: str | Path,
    disposition: str = DispositionType.WONTFIX,
) -> bool:
    """Add disposition entry. Returns True if added, False if exists."""
    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO finding_dispositions (task_id, file, line, reason, disposition) VALUES (?, ?, ?, ?, ?)",
            (task_id, file, line, reason, disposition),
        )
        return cursor.rowcount > 0


def delete_wontfix_entry(
    task_id: int,
    file: str,
    line: int | None,
    db_path: str | Path,
) -> bool:
    """Delete disposition entry. Returns True if deleted, False if not found."""
    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM finding_dispositions WHERE task_id = ? AND file = ? AND line IS ?",
            (task_id, file, line),
        )
        return cursor.rowcount > 0
