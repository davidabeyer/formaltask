"""DatabaseConnection - Context manager for SQLite with WAL mode."""

import logging
import sqlite3

__all__: list[str] = ["DatabaseConnection"]

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Context manager for SQLite database connections."""

    def __init__(self, db_path, exclusive=False):
        self.db_path = str(db_path)
        self.exclusive = exclusive
        self.connection = None
        self._skip_wal = "/tmp/" in self.db_path or "pytest" in self.db_path

    def __enter__(self):
        isolation = "EXCLUSIVE" if self.exclusive else None
        self.connection = sqlite3.connect(self.db_path, isolation_level=isolation)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        if not self._skip_wal:
            result = self.connection.execute("PRAGMA journal_mode=WAL").fetchone()
            if result[0] != "wal":
                logger.warning(f"WAL mode not enabled: {result[0]}")
        self.connection.execute("PRAGMA busy_timeout=5000")
        if self.exclusive:
            self.connection.execute("BEGIN EXCLUSIVE")
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            if self.exclusive:
                if exc_type is None:
                    self.connection.commit()
                else:
                    self.connection.rollback()
            self.connection.close()
        return False
