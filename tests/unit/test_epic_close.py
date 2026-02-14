"""Tests for epic_close command - Archive epics when all tasks complete."""

from pathlib import Path

import pytest

from formaltask.cli.commands.epic_close import epic_close
from formaltask.epics import archive_epic, get_epic_status
from formaltask.tasks.crud import defer_task
from formaltask.tasks.lifecycle import transition_task_status


def test_archive_epic_not_found_raises_error(db_path, repo):
    """Test that archive_epic raises ValueError for non-existent epic."""
    with pytest.raises(ValueError, match="Epic 'nonexistent' not found"):
        archive_epic(db_path, "nonexistent")


def test_archive_epic_incomplete_tasks_raises_error(db_path, repo):
    """Test that archive_epic raises error when tasks are incomplete."""
    repo.create_epic("test-epic", "Test description")
    repo.create_task(
        epic_name="test-epic",
        title="Incomplete task",
        description="Not done",
        criteria=["Criterion 1"],
    )

    with pytest.raises(ValueError, match="Cannot archive.*incomplete tasks"):
        archive_epic(db_path, "test-epic")


def test_archive_epic_force_ignores_incomplete_tasks(db_path, repo):
    """Test that archive_epic with force=True archives even with incomplete tasks."""
    repo.create_epic("test-epic", "Test description")
    repo.create_task(
        epic_name="test-epic",
        title="Incomplete task",
        description="Not done",
        criteria=["Criterion 1"],
    )

    archive_epic(db_path, "test-epic", force=True)

    status = get_epic_status(db_path, "test-epic")
    assert status["status"] == "archived"


def test_epic_close_command_returns_status(db_path, repo):
    """Test that epic_close CLI command returns expected dict."""
    repo.create_epic("test-epic", "Test description")
    task_id = repo.create_task(
        epic_name="test-epic",
        title="Test task",
        description="Test description",
        criteria=["Criterion 1"],
    )
    transition_task_status(db_path, task_id, "in_progress")
    repo.complete_task(task_id)

    result = epic_close("test-epic", db_path=db_path)

    assert result["epic_name"] == "test-epic"
    assert result["status"] == "archived"


def test_pm_epic_close_dispatches_to_command(db_path, repo, monkeypatch):
    """Test that pm.py epic-close subcommand dispatches correctly."""
    import sys

    repo.create_epic("test-epic", "Test description")
    task_id = repo.create_task(
        epic_name="test-epic",
        title="Test task",
        description="Test description",
        criteria=["Criterion 1"],
    )
    transition_task_status(db_path, task_id, "in_progress")
    repo.complete_task(task_id)

    # Mock sys.argv to simulate CLI call
    monkeypatch.setattr(sys, "argv", ["pm", "epic", "close", "test-epic", "--db-path", db_path])

    from formaltask.cli.pm import main

    result = main()

    assert result == 0
    status = get_epic_status(db_path, "test-epic")
    assert status["status"] == "archived"


def test_epic_close_moves_project_directory(db_path, repo, tmp_path):
    """Test that epic_close moves project directory to Archive folder."""
    # Setup: Create project directory structure
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    project_dir = projects_dir / "test-epic"
    project_dir.mkdir()
    (project_dir / "plans").mkdir()
    (project_dir / "PRPs").mkdir()
    (project_dir / "plans" / "plan.md").write_text("# Plan")

    # Create and complete epic
    repo.create_epic("test-epic", "Test description")
    task_id = repo.create_task(
        epic_name="test-epic",
        title="Test task",
        description="Test description",
        criteria=["Criterion 1"],
    )
    transition_task_status(db_path, task_id, "in_progress")
    repo.complete_task(task_id)

    result = epic_close("test-epic", db_path=db_path, projects_dir=str(projects_dir))

    # Verify moved to Archive
    archive_dir = projects_dir / "Archive" / "test-epic"
    assert archive_dir.exists()
    assert (archive_dir / "plans" / "plan.md").exists()
    assert not project_dir.exists()
    assert result["project_moved"] is True
    assert result["moved_to"] == str(archive_dir)


def test_epic_close_handles_archive_collision(db_path, repo, tmp_path):
    """Test that epic_close handles naming collision with timestamp suffix."""
    # Setup: Create project and existing archive with same name
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    project_dir = projects_dir / "test-epic"
    project_dir.mkdir()
    (project_dir / "new-file.txt").write_text("new content")

    archive_dir = projects_dir / "Archive"
    archive_dir.mkdir()
    existing_archive = archive_dir / "test-epic"
    existing_archive.mkdir()
    (existing_archive / "old-file.txt").write_text("old content")

    # Create and complete epic
    repo.create_epic("test-epic", "Test description")
    task_id = repo.create_task(
        epic_name="test-epic",
        title="Test task",
        description="Test description",
        criteria=["Criterion 1"],
    )
    transition_task_status(db_path, task_id, "in_progress")
    repo.complete_task(task_id)

    result = epic_close("test-epic", db_path=db_path, projects_dir=str(projects_dir))

    # Original archive should still exist
    assert existing_archive.exists()
    assert (existing_archive / "old-file.txt").exists()

    # New archive should have timestamp suffix
    assert result["project_moved"] is True
    assert result["moved_to"] != str(existing_archive)
    assert "test-epic_" in result["moved_to"]
    moved_path = Path(result["moved_to"])
    assert moved_path.exists()
    assert (moved_path / "new-file.txt").exists()


def test_pm_epic_close_with_projects_dir_flag(db_path, repo, tmp_path, monkeypatch):
    """Test that pm.py epic-close passes --projects-dir to move project."""
    import sys

    # Setup project directory
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    project_dir = projects_dir / "test-epic"
    project_dir.mkdir()
    (project_dir / "file.txt").write_text("content")

    # Create and complete epic
    repo.create_epic("test-epic", "Test description")
    task_id = repo.create_task(
        epic_name="test-epic",
        title="Test task",
        description="Test description",
        criteria=["Criterion 1"],
    )
    transition_task_status(db_path, task_id, "in_progress")
    repo.complete_task(task_id)

    # Mock sys.argv with --projects-dir flag
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pm",
            "epic", "close",
            "test-epic",
            "--db-path",
            db_path,
            "--projects-dir",
            str(projects_dir),
        ],
    )

    from formaltask.cli.pm import main

    result = main()

    assert result == 0
    # Verify project was moved
    archive_dir = projects_dir / "Archive" / "test-epic"
    assert archive_dir.exists()
    assert not project_dir.exists()


def test_epic_close_rejects_path_traversal(db_path, repo, tmp_path):
    """Test that epic_close rejects epic names with path traversal."""
    # Create a malicious epic name with path traversal
    malicious_name = "../../../etc/passwd"
    repo.create_epic(malicious_name, "Test description")
    task_id = repo.create_task(
        epic_name=malicious_name,
        title="Test task",
        description="Test description",
        criteria=["Criterion 1"],
    )
    transition_task_status(db_path, task_id, "in_progress")
    repo.complete_task(task_id)

    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    with pytest.raises(ValueError, match="path traversal"):
        epic_close(malicious_name, db_path=db_path, projects_dir=str(projects_dir))


def test_archive_epic_empty_epic_succeeds(db_path, repo):
    """Test that archive_epic succeeds on epic with zero tasks."""
    repo.create_epic("empty-epic", "Epic with no tasks")

    # Should not raise - empty epic has no incomplete tasks
    archive_epic(db_path, "empty-epic")

    status = get_epic_status(db_path, "empty-epic")
    assert status["status"] == "archived"


def test_archive_epic_deferred_tasks_blocks(db_path, repo):
    """Test that archive_epic blocks when epic has deferred (non-completed) tasks."""
    repo.create_epic("deferred-epic", "Epic with deferred task")
    task_id = repo.create_task(
        epic_name="deferred-epic",
        title="Deferred task",
        description="Task that was deferred",
        criteria=["Criterion 1"],
    )
    transition_task_status(db_path, task_id, "in_progress")
    defer_task(db_path, task_id, reason="Out of scope for MVP")

    # Deferred tasks are not completed - should block archiving
    with pytest.raises(ValueError, match="Cannot archive.*incomplete tasks"):
        archive_epic(db_path, "deferred-epic")


def test_execute_rejects_symlink_db_path(tmp_path, capsys):
    """execute() rejects symlink --db-path for security (Task #1965)."""
    from argparse import Namespace

    from formaltask.cli.commands import epic_close as epic_close_module

    # Create real db and symlink to it
    real_db = tmp_path / "real.db"
    real_db.touch()
    symlink_db = tmp_path / "link.db"
    symlink_db.symlink_to(real_db)

    args = Namespace(
        db_path=str(symlink_db), epic_name="test", force=False, projects_dir=None, json=False
    )
    result = epic_close_module.execute(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "symlink" in captured.out.lower() or "symlink" in captured.err.lower()
