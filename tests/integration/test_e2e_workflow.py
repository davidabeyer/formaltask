"""End-to-end integration test for complete FormalTask workflow.

Task #1047: Tests the complete flow: decompose → finalize → verify
Updated for Task #2862: Uses spec directories instead of PRP files.
"""

import sqlite3
from unittest.mock import patch

import pytest

from tests.fixtures.paths import SCHEMA_FILE


@pytest.fixture
def test_db(tmp_path):
    """Create test database with FormalTask schema."""
    db_file = tmp_path / "test_formaltask.db"

    # Use centralized path constants (Task #2128)
    # Note: SQL migrations removed in Task #2654 - schema-v5.sql is source of truth
    with sqlite3.connect(db_file) as conn:
        with open(SCHEMA_FILE) as f:
            conn.executescript(f.read())
        conn.commit()

    return db_file


@pytest.fixture
def spec_dir(tmp_path):
    """Create a spec directory with task YAML files.

    Uses tmp_path because _validate_spec_dir_path only allows paths within:
    - Path.home() / "projects"
    - PROJECT_ROOT (resolved from cwd when running tests)
    """
    spec_path = tmp_path / "e2e-workflow-specs"
    spec_path.mkdir()

    # Task 1: Setup Database Schema
    task1_spec = """
title: "Task 1: Setup Database Schema"
summary: Create the initial database schema.
context: Set up the foundation for data storage.
implementation:
  - Create schema file
  - Define tables
acceptance_criteria:
  - id: c-1
    current: Schema file exists
    command: "test -f schema.sql"
    history: []
testing:
  - Verify schema loads
depends_on: []
required_reviews: []
skills: []
"""
    (spec_path / "task-1-setup-schema.yaml").write_text(task1_spec)

    # Task 2: Implement Repository Layer
    task2_spec = """
title: "Task 2: Implement Repository Layer"
summary: Build the repository pattern.
context: Create data access layer on top of schema.
implementation:
  - Create repository class
  - Add CRUD methods
acceptance_criteria:
  - id: c-2
    current: Repository class created
    command: "grep -q 'class Repository' repository.py"
    history: []
testing:
  - Unit tests for repository
depends_on: [1]
required_reviews: []
skills: []
"""
    (spec_path / "task-2-repository-layer.yaml").write_text(task2_spec)

    return spec_path


def test_decompose_creates_tasks_from_specs(test_db, spec_dir):
    """Test that epic_decompose creates tasks from spec directory."""
    from formaltask.cli.commands.epic_decompose import epic_decompose

    # Setup: Create epic in database
    epic_name = "e2e-workflow-test"
    with sqlite3.connect(test_db) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            (epic_name, "E2E Test", "2025-01-15T00:00:00Z"),
        )
        conn.commit()

    # Patch _PROJECT_ROOT to allow test fixture path (Task #1197)
    # Path validation is tested separately; this test focuses on decompose workflow
    with patch(
        "formaltask.cli.commands.epic_decompose._PROJECT_ROOT",
        spec_dir.parent,
    ):
        # Decompose
        task_ids = epic_decompose(
            epic_name=epic_name,
            spec_dir_path=str(spec_dir),
            db_path=str(test_db),
        )

    # Verify 2 tasks created
    assert len(task_ids) == 2


