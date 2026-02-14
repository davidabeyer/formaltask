"""Integration test for epic-yaml-elimination epic.

Task #2865: Validates entire epic worked together:
- parse_specs_dir() → epic_decompose() → DB tasks roundtrip
- parse_specs_dir() output has all required keys
- Spec validation raises SpecFormatError for missing required fields
- No epic.yaml references remain in skills/ or agents/
- No epic.yaml files exist in .plans/

Updated for spec-directory parsing (Task #2862).
"""

import sqlite3
import subprocess
from unittest.mock import patch

import pytest

from formaltask.epics.yaml_parser import SpecFormatError
from tests.fixtures.paths import PROJECT_ROOT, SCHEMA_FILE


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
def spec_dir(tmp_path):
    """Create a spec directory with valid task YAML files."""
    spec_path = tmp_path / "test-epic-specs"
    spec_path.mkdir()

    # Task 1: Core Parser
    task1_spec = """
title: "Task 1: Core Parser"
summary: Create the core parser for spec files.
context: Foundation for parsing spec directories.
implementation:
  - Create parser module
  - Add validation logic
acceptance_criteria:
  - id: c-1
    current: Parser function exists
    command: "test -f parser.py"
    history: []
testing:
  - Unit tests for parser
depends_on: []
required_reviews: []
skills: []
"""
    (spec_path / "task-1-core-parser.yaml").write_text(task1_spec)

    # Task 2: Validation Layer
    task2_spec = """
title: "Task 2: Validation Layer"
summary: Add validation on top of parser.
context: Ensure parsed specs are valid.
implementation:
  - Create validator
  - Add error handling
acceptance_criteria:
  - id: c-2
    current: Validator function exists
    command: "grep -q 'def validate' validator.py"
    history: []
testing:
  - Unit tests for validator
depends_on: [1]
required_reviews: []
skills: []
"""
    (spec_path / "task-2-validation-layer.yaml").write_text(task2_spec)

    return spec_path


@pytest.fixture
def invalid_spec_dir(tmp_path):
    """Create a spec directory with invalid spec (missing title)."""
    spec_path = tmp_path / "invalid-specs"
    spec_path.mkdir()

    # Spec without title - should fail validation
    invalid_spec = """
summary: This spec is missing a title field.
context: Testing validation.
implementation:
  - Do something
acceptance_criteria:
  - id: c-1
    current: Something happens
    history: []
testing:
  - Test something
depends_on: []
required_reviews: []
skills: []
"""
    (spec_path / "task-1-no-title.yaml").write_text(invalid_spec)

    return spec_path


def test_parse_specs_to_epic_decompose_roundtrip(test_db, spec_dir):
    """Test parse_specs_dir() → epic_decompose() → DB tasks roundtrip.

    Verifies that:
    1. parse_specs_dir() returns list of task dicts
    2. epic_decompose() accepts this output and creates DB tasks
    3. Created tasks have correct titles, descriptions, criteria
    """
    from formaltask.cli.commands.epic_decompose import epic_decompose
    from formaltask.epics.yaml_parser import parse_specs_dir

    # Setup: Create epic in database
    epic_name = "test-epic"
    with sqlite3.connect(test_db) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            (epic_name, "Test Epic", "2025-01-15T00:00:00Z"),
        )
        conn.commit()

    # Parse spec directory
    tasks = parse_specs_dir(str(spec_dir))

    # Verify parser output
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Task 1: Core Parser"
    assert tasks[1]["title"] == "Task 2: Validation Layer"

    # Patch _PROJECT_ROOT to allow test fixture path
    with patch(
        "formaltask.cli.commands.epic_decompose._PROJECT_ROOT",
        spec_dir.parent,
    ):
        # Decompose - should accept parse_specs_dir() output without errors
        task_ids = epic_decompose(
            epic_name=epic_name,
            spec_dir_path=str(spec_dir),
            db_path=str(test_db),
        )

    # Verify tasks created in DB
    assert len(task_ids) == 2

    # Verify task details in DB
    with sqlite3.connect(test_db) as conn:
        rows = conn.execute(
            "SELECT id, title, description FROM tasks ORDER BY id"
        ).fetchall()

        assert len(rows) == 2
        assert rows[0][1] == f"{epic_name}: Task 1: Core Parser"
        assert rows[0][2] == "Create the core parser for spec files."
        assert rows[1][1] == f"{epic_name}: Task 2: Validation Layer"
        assert rows[1][2] == "Add validation on top of parser."

        # Verify acceptance criteria
        criteria = conn.execute(
            "SELECT task_id, text FROM acceptance_criteria ORDER BY task_id, id"
        ).fetchall()
        assert len(criteria) == 2
        assert criteria[0][1] == "Parser function exists"
        assert criteria[1][1] == "Validator function exists"


def test_parse_specs_dir_output_keys(spec_dir):
    """Test parse_specs_dir() output has all keys epic_decompose() consumes.

    Ensures no KeyError when epic_decompose() accesses parse_specs_dir() output.
    """
    from formaltask.epics.yaml_parser import parse_specs_dir

    tasks = parse_specs_dir(str(spec_dir))

    # epic_decompose() requires these keys (see epic_decompose.py:110-155)
    required_keys = {
        "title",
        "description",
        "criteria",
        "spec_content",
        "depends_on",
        "required_reviews",
        "skills",
        "documentation_required",
    }

    for i, task in enumerate(tasks, 1):
        missing_keys = required_keys - set(task.keys())
        assert not missing_keys, f"Task {i} missing keys: {missing_keys}"

        # Verify types
        assert isinstance(task["title"], str), f"Task {i} title not str"
        assert isinstance(task["description"], str), f"Task {i} description not str"
        assert isinstance(task["criteria"], list), f"Task {i} criteria not list"
        assert isinstance(task["spec_content"], str), f"Task {i} spec_content not str"
        assert isinstance(task["depends_on"], list), f"Task {i} depends_on not list"
        assert isinstance(task["required_reviews"], list), f"Task {i} required_reviews not list"
        assert isinstance(task["skills"], list), f"Task {i} skills not list"


def test_spec_without_title_raises_error(invalid_spec_dir):
    """Test spec files without title raise SpecFormatError.

    SpecSpec model should reject specs missing required fields.
    """
    from formaltask.epics.yaml_parser import parse_specs_dir

    with pytest.raises(SpecFormatError, match="Spec validation failed"):
        parse_specs_dir(str(invalid_spec_dir))


def test_no_epic_yaml_references_in_code():
    """Test no epic.yaml references exist in skills/ or agents/.

    Runs: grep -r 'epic\\.yaml' skills/ agents/ | grep -v '#\\|//\\|historical'
    Should return 0 matches (exit code 1 from grep means no matches).
    """
    # Run grep to find epic.yaml references (excluding comments)
    result = subprocess.run(
        ["bash", "-c", "grep -r 'epic\\.yaml' skills/ agents/ 2>/dev/null | grep -v '#\\|//\\|historical' || true"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should have no output (all references filtered out)
    assert result.stdout.strip() == "", (
        f"Found epic.yaml references in skills/ or agents/:\n{result.stdout}"
    )


def test_no_epic_yaml_files_in_plans():
    """Test no epic.yaml files exist in .plans/.

    Runs: find .plans -name 'epic.yaml'
    Should return 0 results.
    """
    plans_dir = PROJECT_ROOT / ".plans"

    if not plans_dir.exists():
        pytest.skip(".plans directory does not exist")

    # Find epic.yaml files
    result = subprocess.run(
        ["find", str(plans_dir), "-name", "epic.yaml"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should have no output
    assert result.stdout.strip() == "", (
        f"Found epic.yaml files in .plans/:\n{result.stdout}"
    )
