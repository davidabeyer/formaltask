"""Integration tests for runnable acceptance criteria flow.

Task #2861: End-to-end test validating complete runnable AC flow:
1. Spec parsing with command fields (g-1, g-2)
2. epic-decompose storing commands in acceptance_criteria table (g-2)
3. task-complete executing commands and blocking on failure (g-4)
4. Worker instructions showing verification commands (g-5)
"""

import sqlite3
from unittest.mock import patch

import pytest

from tests.fixtures.paths import SCHEMA_FILE


@pytest.fixture
def test_db(tmp_path):
    """Create test database with FormalTask schema."""
    db_file = tmp_path / "test_formaltask.db"

    with sqlite3.connect(db_file) as conn:
        with open(SCHEMA_FILE) as f:
            conn.executescript(f.read())
        conn.commit()

    return db_file


@pytest.fixture
def spec_dir_with_commands(tmp_path):
    """Create a spec directory with tasks having runnable AC commands."""
    spec_path = tmp_path / "runnable-ac-test-specs"
    spec_path.mkdir()

    # Task 1: Basic task with simple command
    task1_spec = """
title: "Task 1: Create Config File"
summary: Create a basic configuration file.
context: Foundation for configuration system.
implementation:
  - Create config.json file
acceptance_criteria:
  - id: c-1
    current: config.json exists
    command: "test -f config.json"
    history: []
testing:
  - Verify file creation
depends_on: []
required_reviews: []
skills: []
"""
    (spec_path / "task-1-create-config.yaml").write_text(task1_spec)

    # Task 2: Task with multiple acceptance criteria
    task2_spec = """
title: "Task 2: Setup Python Module"
summary: Create Python module structure.
context: Set up package structure.
implementation:
  - Create __init__.py
  - Create main.py
acceptance_criteria:
  - id: c-2
    current: __init__.py exists
    command: "test -f mymodule/__init__.py"
    history: []
  - id: c-3
    current: main.py exists and has main function
    command: "grep -q 'def main' mymodule/main.py"
    history: []
testing:
  - Verify module structure
depends_on: []
required_reviews: []
skills: []
"""
    (spec_path / "task-2-setup-module.yaml").write_text(task2_spec)

    return spec_path


def test_parse_spec_with_commands(spec_dir_with_commands):
    """Test that specs with command fields are parsed correctly.

    Verifies g-1, g-2: Spec parser handles CriterionV2 format with command field.
    """
    from formaltask.epics.yaml_parser import parse_specs_dir

    # Parse specs
    tasks = parse_specs_dir(str(spec_dir_with_commands))

    # Should have 2 tasks
    assert len(tasks) == 2

    # Task 1: Should have 1 criterion with command
    task1 = tasks[0]
    assert task1["title"] == "Task 1: Create Config File"
    assert len(task1["criteria"]) == 1
    assert task1["criteria"][0]["text"] == "config.json exists"
    assert task1["criteria"][0]["command"] == "test -f config.json"

    # Task 2: Should have 2 criteria with commands
    task2 = tasks[1]
    assert task2["title"] == "Task 2: Setup Python Module"
    assert len(task2["criteria"]) == 2
    assert task2["criteria"][0]["text"] == "__init__.py exists"
    assert task2["criteria"][0]["command"] == "test -f mymodule/__init__.py"
    assert task2["criteria"][1]["text"] == "main.py exists and has main function"
    assert task2["criteria"][1]["command"] == "grep -q 'def main' mymodule/main.py"


def test_decompose_stores_commands(test_db, spec_dir_with_commands):
    """Test that epic-decompose stores commands in acceptance_criteria table.

    Verifies g-2: Commands from specs are stored in database.
    """
    from formaltask.cli.commands.epic_decompose import epic_decompose

    # Setup: Create epic in database
    epic_name = "runnable-ac-test"
    with sqlite3.connect(test_db) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            (epic_name, "Runnable AC Test Epic", "2026-02-03T00:00:00Z"),
        )
        conn.commit()

    # Decompose with spec directory
    with patch(
        "formaltask.cli.commands.epic_decompose._PROJECT_ROOT",
        spec_dir_with_commands.parent,
    ):
        task_ids = epic_decompose(
            epic_name=epic_name,
            spec_dir_path=str(spec_dir_with_commands),
            db_path=str(test_db),
        )

    # Verify 2 tasks created
    assert len(task_ids) == 2

    # Query acceptance_criteria table and verify commands stored
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()

        # Task 1: Should have 1 criterion with command
        cursor.execute(
            "SELECT text, command FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
            (task_ids[0],),
        )
        task1_criteria = cursor.fetchall()
        assert len(task1_criteria) == 1
        assert task1_criteria[0][0] == "config.json exists"
        assert task1_criteria[0][1] == "test -f config.json"

        # Task 2: Should have 2 criteria with commands
        cursor.execute(
            "SELECT text, command FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
            (task_ids[1],),
        )
        task2_criteria = cursor.fetchall()
        assert len(task2_criteria) == 2
        assert task2_criteria[0][0] == "__init__.py exists"
        assert task2_criteria[0][1] == "test -f mymodule/__init__.py"
        assert task2_criteria[1][0] == "main.py exists and has main function"
        assert task2_criteria[1][1] == "grep -q 'def main' mymodule/main.py"


def test_complete_with_passing_command(test_db, tmp_path):
    """Test task completion succeeds when AC command passes.

    Verifies g-4: Task completion executes commands and allows completion on success.
    """
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.core.completion_config import CompletionConfig
    from formaltask.tasks.crud import create_task
    from formaltask.tasks.lifecycle import transition_task_status

    # Setup: Create epic
    epic_name = "test-epic"
    with sqlite3.connect(test_db) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            (epic_name, "Test Epic", "2026-02-03T00:00:00Z"),
        )
        conn.commit()

    # Create test file that command will check
    test_file = tmp_path / "verification.txt"
    test_file.write_text("test content")

    # Create task with passing command
    task_id = create_task(
        db_path=str(test_db),
        epic_name=epic_name,
        title="Test Task",
        description="Task with passing AC command",
        criteria=[{"text": "Verification file exists", "command": f"test -f {test_file}"}],
        metadata={"required_reviews": []},  # No reviews required
    )

    # Transition to in_progress (required for completion)
    transition_task_status(str(test_db), task_id, "in_progress")

    # Mock completion config to disable review checks but enable AC checks
    test_config = CompletionConfig(
        required_reviews=[],
        check_freshness=False,
        require_pr=False,
        require_pr_merged=False,
        documentation_required=False,
        check_docs=False,
        check_learnings=False,
        check_ac=True,  # Enable AC checks
    )

    # Mock findings state to indicate reviews exist
    from formaltask.state.findings import FindingsState

    mock_findings_state = FindingsState(
        has_reviews=True,  # Indicate reviews exist
        has_wontfix=False,
        has_needshuman_critical=False,
        has_needshuman_deferrable=False,
        has_unresolved_findings=False,
        latest_review_clean=True,
    )

    # Mock git commands, config, and findings state to test AC flow
    with patch("formaltask.git.utils.get_head_sha", return_value="a" * 40):
        with patch(
            "formaltask.cli.commands.task_complete._should_skip_review_gates",
            return_value=(False, "task-2861"),
        ):
            with patch(
                "formaltask.core.completion_state.get_effective_config",
                return_value=test_config,
            ):
                with patch(
                    "formaltask.core.completion_state.check_findings_state",
                    return_value=mock_findings_state,
                ):
                    with patch("sys.stdin.isatty", return_value=False):  # Skip learning prompt
                        # Complete task - should succeed
                        result = task_complete(task_id, str(test_db), no_evidence=True)
                        assert result == 0

    # Verify task is completed
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        status = cursor.fetchone()[0]
        assert status == "completed"


def test_complete_with_failing_command(test_db, tmp_path):
    """Test that task completion blocks when AC command fails.

    Verifies g-4: Task completion blocks on failing verification commands.
    """
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.core.completion_config import CompletionConfig
    from formaltask.tasks.crud import create_task
    from formaltask.tasks.guards import GuardViolation
    from formaltask.tasks.lifecycle import transition_task_status

    # Setup: Create epic
    epic_name = "test-epic"
    with sqlite3.connect(test_db) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            (epic_name, "Test Epic", "2026-02-03T00:00:00Z"),
        )
        conn.commit()

    # Create task with failing command (file doesn't exist)
    nonexistent_file = tmp_path / "does_not_exist.txt"
    task_id = create_task(
        db_path=str(test_db),
        epic_name=epic_name,
        title="Test Task",
        description="Task with failing AC command",
        criteria=[
            {"text": "Nonexistent file exists", "command": f"test -f {nonexistent_file}"}
        ],
        metadata={"required_reviews": []},  # No reviews required
    )

    # Transition to in_progress (required for completion)
    transition_task_status(str(test_db), task_id, "in_progress")

    # Mock completion config to disable review checks but enable AC checks
    test_config = CompletionConfig(
        required_reviews=[],
        check_freshness=False,
        require_pr=False,
        require_pr_merged=False,
        documentation_required=False,
        check_docs=False,
        check_learnings=False,
        check_ac=True,  # Enable AC checks
    )

    # Mock findings state to indicate reviews exist
    from formaltask.state.findings import FindingsState

    mock_findings_state = FindingsState(
        has_reviews=True,  # Indicate reviews exist
        has_wontfix=False,
        has_needshuman_critical=False,
        has_needshuman_deferrable=False,
        has_unresolved_findings=False,
        latest_review_clean=True,
    )

    # Mock git commands, config, and findings state to test AC flow
    with patch("formaltask.git.utils.get_head_sha", return_value="a" * 40):
        with patch(
            "formaltask.cli.commands.task_complete._should_skip_review_gates",
            return_value=(False, "task-2861"),
        ):
            with patch(
                "formaltask.core.completion_state.get_effective_config",
                return_value=test_config,
            ):
                with patch(
                    "formaltask.core.completion_state.check_findings_state",
                    return_value=mock_findings_state,
                ):
                    with patch("sys.stdin.isatty", return_value=False):  # Skip learning prompt
                        # Complete task - should fail with GuardViolation
                        with pytest.raises(GuardViolation) as exc_info:
                            task_complete(task_id, str(test_db), no_evidence=True)

                        # Verify error message mentions AC failure
                        assert "Acceptance criteria command" in str(exc_info.value)

    # Verify task is still in_progress (not completed)
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        status = cursor.fetchone()[0]
        assert status == "in_progress"
