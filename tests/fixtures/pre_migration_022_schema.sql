-- Pre-migration schema for testing migration 022_add_head_commit_sha.sql
-- This represents the database state BEFORE migration 022 was applied.
-- Minimal schema with just the tables needed for migration testing.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS epics (
    name TEXT PRIMARY KEY NOT NULL,
    description TEXT NOT NULL,
    skip_review BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_name TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    position INTEGER,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    -- NOTE: head_commit_sha column intentionally omitted - added by migration 022
    -- NOTE: pr_merged column removed (Task #2186) - no longer in schema
    FOREIGN KEY (epic_name) REFERENCES epics(name) ON DELETE CASCADE
);

INSERT OR IGNORE INTO epics (name, description, skip_review, created_at)
VALUES ('master-adhoc', 'Unplanned work and hotfixes', TRUE, datetime('now'));
