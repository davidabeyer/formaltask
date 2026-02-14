-- FormalTask v5 Database Schema
-- SQLite 3.35+ required for WAL mode support
-- 11 tables with migration columns

-- Enable foreign keys (WAL mode enabled by db_connection.py at runtime)
PRAGMA foreign_keys = ON;

-- Table 1: epics (7 fields)
CREATE TABLE IF NOT EXISTS epics (
    name TEXT PRIMARY KEY NOT NULL,
    description TEXT NOT NULL,
    skip_review BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    reviewed_at TEXT,  -- Added by migration 025: tracks last pm-epic-review run
    feature_branch TEXT  -- Added by migration add_epic_feature_branch
);

-- Table 2: tasks (31 fields) - GitHub columns removed by migration 018, metadata flattened by Task #2588
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_name TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'completed', 'cancelled', 'deferred', 'pending_merge', 'blocked', 'pending_review', 'blocked_user')),
    position INTEGER,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    metadata TEXT CHECK (metadata IS NULL OR json_valid(metadata) = 1),  -- JSON column for arrays/complex fields only
    -- created_from_review_of column REMOVED by Task #2759 (dead code - never wired up)
    -- Added by migration 008
    depends_on TEXT DEFAULT '[]',
    is_parallel INTEGER DEFAULT 1,
    -- parallel_safe column REMOVED by migration 025 (Task #1991)
    spawned_at TEXT,
    -- Added by migration 010
    acceptance_criteria_json TEXT,
    -- github_pr_number column REMOVED by Task #2185 (Schema Migration)
    -- review_status column REMOVED by Task #2013 (RS-6 deprecation)
    review_started_at TEXT,
    review_completed_at TEXT,
    review_attempt INTEGER DEFAULT 0,
    -- Added by migration 013
    last_review_sha TEXT,
    -- pr_merged column REMOVED by Task #2185 (Schema Migration)
    -- Added by migration 022 (Task #1829)
    head_commit_sha TEXT,
    -- Added by migration 028 (Task #2011)
    artifacts_json TEXT,
    -- Added by migration 029 (Task #2018)
    starting_sha TEXT,
    -- Added by Task #1893 (completion evidence for already-done tasks)
    completion_evidence TEXT,
    -- Added by Task #2386
    blocked_question TEXT,
    -- Task #2588: Flattened metadata columns (antirez style - scalar fields as columns)
    defer_reason TEXT CHECK (defer_reason IS NULL OR length(defer_reason) >= 20),
    cancel_reason TEXT,
    cancelled_at TEXT,
    session_id TEXT,
    review_round INTEGER CHECK (review_round IS NULL OR review_round > 0),
    pr_url TEXT CHECK (pr_url IS NULL OR pr_url LIKE 'http://%' OR pr_url LIKE 'https://%'),
    artifact_type TEXT CHECK (artifact_type IS NULL OR artifact_type = 'spec'),
    FOREIGN KEY (epic_name) REFERENCES epics(name) ON DELETE CASCADE
);

-- Table 3: acceptance_criteria (6 fields) - command added by Task #2859
CREATE TABLE IF NOT EXISTS acceptance_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    checked BOOLEAN DEFAULT FALSE,
    evidence TEXT,
    command TEXT,  -- Added by Task #2859: runnable acceptance criteria command
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Table 4: commits (3 fields)
CREATE TABLE IF NOT EXISTS commits (
    task_id INTEGER NOT NULL,
    commit_hash TEXT NOT NULL,
    commit_message TEXT,
    PRIMARY KEY (task_id, commit_hash),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Table 5: task_reviews (11 fields) - Renamed from automated_reviews by migration 026
-- PK changed to (task_id, review_type, round) by add_review_sha_and_round migration
CREATE TABLE IF NOT EXISTS task_reviews (
    task_id INTEGER NOT NULL,
    review_type TEXT NOT NULL DEFAULT 'code-quality',  -- Added by add_review_type migration
    severity TEXT NOT NULL,  -- CHECK constraint removed: doesn't exist in production (Task #2778)
    findings TEXT NOT NULL,       -- JSON array of finding objects
    reviewed_at TEXT NOT NULL,
    followup_task_id INTEGER,     -- Links to follow-up task if created
    ignored BOOLEAN DEFAULT 0,
    ignored_reason TEXT,
    source TEXT DEFAULT 'claude',  -- Added by migration 012
    round INTEGER NOT NULL DEFAULT 1,  -- Added by Task #1995: Review round for history preservation
    reviewed_sha TEXT,            -- Added by add_review_sha_and_round migration
    PRIMARY KEY (task_id, review_type, round),  -- Composite PK for review history
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (followup_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Table 6: work_sessions (2 fields)
CREATE TABLE IF NOT EXISTS work_sessions (
    worktree_path TEXT PRIMARY KEY NOT NULL,
    current_task_id INTEGER,
    FOREIGN KEY (current_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Task #2653: workers table REMOVED (dead code - written but never read, staleness from transcript mtime)
-- Task #2770: Table 7 REMOVED (dead code - event sourcing written but never read)

-- Table 9: finding_dispositions - Track findings with dispositions (Task #2114)
-- Task #2261: Added disposition column for needshuman support
-- Task #2294: line column now nullable for file-level findings without line numbers
-- Task #2598: Renamed from wontfix_findings, added 'fixed' disposition
CREATE TABLE IF NOT EXISTS finding_dispositions (
    task_id INTEGER NOT NULL,
    file TEXT NOT NULL,
    line INTEGER,  -- Nullable for file-level findings (Task #2294)
    reason TEXT NOT NULL CHECK(length(reason) <= 10000),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    disposition TEXT NOT NULL DEFAULT 'wontfix' CHECK(disposition IN ('wontfix', 'needshuman', 'fixed')),
    PRIMARY KEY (task_id, file, line),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_finding_dispositions_task ON finding_dispositions(task_id);
-- NULL-safe unique constraint (Task #2294): PRIMARY KEY doesn't enforce uniqueness for NULL
CREATE UNIQUE INDEX IF NOT EXISTS idx_finding_dispositions_unique ON finding_dispositions(task_id, file, IFNULL(line, -1));

-- Table 10: plan_documents - Planning documents linked to epics (Task #2155)
CREATE TABLE IF NOT EXISTS plan_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_name TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK(doc_type IN ('PRD', 'Epic', 'PRP', 'Plan', 'Critique')),
    path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (epic_name) REFERENCES epics(name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_plan_documents_epic_name ON plan_documents(epic_name);

-- Table 11: critique_findings REMOVED by Task #2778 (table doesn't exist in production - never migrated)

-- Table 12: task_completion_state REMOVED by Task #2588 (dead table - never wired up)

-- Table 13: planning_state - Planning workflow state (Task #2315)
CREATE TABLE IF NOT EXISTS planning_state (
    project_name TEXT PRIMARY KEY,
    current_stage TEXT NOT NULL,
    last_command TEXT NOT NULL,
    loops TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(loops) = 1),
    updated_at TEXT NOT NULL,
    plan_file_path TEXT  -- Added by Task #2367: stores plan file path directly
);

-- Table 14: schema_migrations - Track applied migrations (Task #2654)
-- Required for Python migrations in formaltask/db/migrations/
CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Indexes for performance (<10ms queries)
CREATE INDEX IF NOT EXISTS idx_tasks_epic_name ON tasks(epic_name);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_started_at ON tasks(started_at);
-- UNIQUE constraint on (epic_name, position) from migration 023
-- Partial index allows NULL positions
CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_epic_position_unique
ON tasks(epic_name, position) WHERE position IS NOT NULL;
-- Indexes from migration 008
CREATE INDEX IF NOT EXISTS idx_tasks_spawned_at ON tasks(spawned_at);
CREATE INDEX IF NOT EXISTS idx_tasks_is_parallel ON tasks(is_parallel);
-- idx_tasks_parallel_safe REMOVED by migration 025 (Task #1991)
-- Indexes from migration 012
-- idx_tasks_review_status REMOVED by Task #2013 (RS-6 deprecation)
CREATE INDEX IF NOT EXISTS idx_criteria_task_id ON acceptance_criteria(task_id);
CREATE INDEX IF NOT EXISTS idx_commits_task_id ON commits(task_id);
CREATE INDEX IF NOT EXISTS idx_task_reviews_severity ON task_reviews(severity);
CREATE INDEX IF NOT EXISTS idx_task_reviews_ignored ON task_reviews(ignored);
CREATE INDEX IF NOT EXISTS idx_task_reviews_followup ON task_reviews(followup_task_id);
-- Index for RS-1 derived state views (Task #2092): optimize joins on task_id and round
CREATE INDEX IF NOT EXISTS idx_task_reviews_task_round ON task_reviews(task_id, round);

-- Triggers for defensive timestamp coordination (from migration 017)
-- These are defense-in-depth: ensure timestamps are set even if code bypasses
-- the transition_task_status() function and does direct SQL updates.

-- Trigger: Auto-set completed_at when status changes to 'completed'
-- Guard: Only fires if completed_at IS NULL (prevents double-update)
CREATE TRIGGER IF NOT EXISTS set_completed_at_on_completion
AFTER UPDATE OF status ON tasks
WHEN NEW.status = 'completed' AND NEW.completed_at IS NULL
BEGIN
    UPDATE tasks
    SET completed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE id = NEW.id;
END;

-- Trigger: Auto-set started_at when status changes to 'in_progress'
-- Guard: Only fires if started_at IS NULL (prevents double-update)
CREATE TRIGGER IF NOT EXISTS set_started_at_on_start
AFTER UPDATE OF status ON tasks
WHEN NEW.status = 'in_progress' AND NEW.started_at IS NULL
BEGIN
    UPDATE tasks
    SET started_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE id = NEW.id;
END;

-- Epic status VIEW (computes state from tasks)
-- Fixed by migration fix_epic_status_completed_count: uses status='completed' not completed_at
CREATE VIEW IF NOT EXISTS epic_status AS
SELECT
    e.name as epic_name,
    e.description,
    e.skip_review,
    e.created_at,
    e.archived_at,
    COUNT(t.id) as total_tasks,
    SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
    SUM(CASE WHEN t.started_at IS NOT NULL AND t.completed_at IS NULL THEN 1 ELSE 0 END) as in_progress_tasks,
    CASE
        WHEN e.archived_at IS NOT NULL THEN 'archived'
        WHEN COUNT(t.id) = 0 THEN 'planning'
        WHEN COUNT(t.id) = SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) THEN 'completed'
        WHEN SUM(CASE WHEN t.started_at IS NOT NULL THEN 1 ELSE 0 END) > 0 THEN 'in_progress'
        ELSE 'open'
    END as status,
    e.reviewed_at
FROM epics e
LEFT JOIN tasks t ON e.name = t.epic_name
GROUP BY e.name;

-- Task ready status VIEW (tasks ready to start: open + all deps satisfied + epic not archived)
-- A task is ready if status='open' AND epic not archived AND (no dependencies OR all dependencies satisfied)
-- "Satisfied" means completed OR cancelled (Task #2750: cancelled tasks don't block dependents)
CREATE VIEW IF NOT EXISTS task_ready_status AS
SELECT
    t.id as task_id,
    t.epic_name,
    t.title,
    t.depends_on
FROM tasks t
JOIN epics e ON t.epic_name = e.name
WHERE t.status = 'open'
  AND e.archived_at IS NULL
  AND (
    -- No dependencies
    t.depends_on IS NULL
    OR t.depends_on = '[]'
    -- Or all dependencies are satisfied (completed or cancelled)
    OR NOT EXISTS (
      SELECT 1
      FROM json_each(t.depends_on) as dep
      JOIN tasks dt ON dt.id = dep.value
      WHERE dt.status NOT IN ('completed', 'cancelled')
    )
  );

-- Task blocked status VIEW (tasks with unsatisfied dependencies)
-- Returns task_id and JSON array of blocking task IDs for tasks that have dependencies not yet completed/cancelled
-- Used by guards.py check_dependencies_satisfied() and spawnable.py --why flag (Task #2752)
CREATE VIEW IF NOT EXISTS task_blocked_status AS
SELECT
    t.id as task_id,
    json_group_array(dt.id) as blocking_task_ids
FROM tasks t
JOIN json_each(t.depends_on) as dep ON 1=1
JOIN tasks dt ON dt.id = dep.value
WHERE t.depends_on IS NOT NULL
  AND t.depends_on != '[]'
  AND dt.status NOT IN ('completed', 'cancelled')
GROUP BY t.id;

-- Insert master-adhoc epic for unplanned work
INSERT OR IGNORE INTO epics (name, description, skip_review, created_at)
VALUES ('master-adhoc', 'Unplanned work and hotfixes', TRUE, datetime('now'));
