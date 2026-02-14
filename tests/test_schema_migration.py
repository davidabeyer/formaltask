"""Tests for v5 schema migration.

Only tests that verify actual behavior (VIEW computation logic).
Schema structure tests removed — db_path fixture validates schema loads.
"""

import sqlite3

import pytest


@pytest.mark.skip(
    reason="WAL tests require real filesystem; db_connection.py skips WAL for tmp_path (/tmp/)"
)
def test_wal_mode_enabled_by_database_connection(db_path):
    """Test that WAL mode is enabled when using DatabaseConnection.

    Note: WAL mode is no longer set in schema-v5.sql (it fails on CI temp
    filesystems). Instead, it's enabled at runtime by db_connection.py
    when using DatabaseConnection class.
    """
    from formaltask.db.connection import DatabaseConnection

    # DatabaseConnection enables WAL mode at runtime
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]

    # DatabaseConnection should enable WAL mode
    assert mode.lower() == "wal", f"Expected WAL mode via DatabaseConnection, got {mode}"


def test_epic_status_view_works(db_path):
    """Test that epic_status VIEW computes state correctly."""
    # db_path fixture already loads schema
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT epic_name, status FROM epic_status WHERE epic_name='master-adhoc'")
        result = cursor.fetchone()

    assert result is not None, "epic_status VIEW should return master-adhoc"
    assert result[0] == "master-adhoc", f"Expected 'master-adhoc', got {result[0]}"
    assert result[1] == "planning", f"Expected status 'planning' for empty epic, got {result[1]}"
