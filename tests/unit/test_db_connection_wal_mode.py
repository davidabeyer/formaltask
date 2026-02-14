"""Tests for DatabaseConnection WAL mode handling in CI environments."""

import sqlite3

from formaltask.db.connection import DatabaseConnection


def test_wal_mode_disabled_for_temp_paths(tmp_path):
    """DatabaseConnection should skip WAL mode for temp paths.

    This prevents CI failures where WAL mode doesn't work reliably
    on temp filesystems, causing 'no such table' errors.
    """
    db_file = tmp_path / "test.db"

    # Create empty database
    sqlite3.connect(db_file).close()

    with DatabaseConnection(str(db_file)) as conn:
        # Check current journal mode
        result = conn.execute("PRAGMA journal_mode").fetchone()
        journal_mode = result[0]

        # For temp paths, should NOT be WAL
        assert journal_mode != "wal", (
            f"WAL mode should be disabled for temp paths, got: {journal_mode}"
        )
