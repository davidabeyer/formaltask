"""Tests for pm learning command.

Task #2353: Implement pm learning command that captures worker learnings
to task metadata for cross-task knowledge sharing.
"""

import json
import sqlite3
from argparse import Namespace

import pytest


@pytest.fixture
def learning_context(db_path, repo, monkeypatch):
    """Create source and target tasks for learning command tests.

    Returns dict with source_id, target_id, db_path.
    Sets TASK_ID env var to source_id.
    """
    repo.create_epic("test-epic", "Test")
    source_id = repo.create_task("test-epic", "Source task", "Desc", ["criterion"])
    target_id = repo.create_task("test-epic", "Target task", "Desc", ["criterion"])
    monkeypatch.setenv("TASK_ID", str(source_id))
    return {"source_id": source_id, "target_id": target_id, "db_path": db_path}


class TestLearningCommand:
    """Tests for the learning command."""

    def test_learning_stored_in_metadata(self, learning_context):
        """pm learning "insight" stores learning in task.metadata.learnings."""
        from formaltask.cli.commands.learning import execute

        args = Namespace(
            learning="Use indexes for queries",
            targets=str(learning_context["target_id"]),
            db_path=learning_context["db_path"],
        )
        result = execute(args)
        assert result == 0

        # Verify learning stored in metadata as object
        with sqlite3.connect(learning_context["db_path"]) as conn:
            row = conn.execute(
                "SELECT metadata FROM tasks WHERE id = ?",
                (learning_context["source_id"],),
            ).fetchone()

        metadata = json.loads(row[0]) if row[0] else {}
        assert "learnings" in metadata
        learning_obj = metadata["learnings"][0]
        assert learning_obj["text"] == "Use indexes for queries"
        assert learning_obj["targets"] == [learning_context["target_id"]]

    def test_learning_too_long_rejected(self, learning_context, capsys):
        """Learning >200 chars returns VALIDATION_ERROR with clear message."""
        from formaltask.cli.commands.learning import execute
        from formaltask.cli.exit_codes import ExitCode

        long_learning = "x" * 201
        args = Namespace(
            learning=long_learning,
            targets=str(learning_context["target_id"]),
            db_path=learning_context["db_path"],
        )
        result = execute(args)

        assert result == ExitCode.VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Learning too long (201 chars). Max 200." in captured.err

    def test_learning_at_200_chars_accepted(self, learning_context):
        """Boundary: exactly 200 chars succeeds."""
        from formaltask.cli.commands.learning import execute

        learning_200 = "x" * 200
        args = Namespace(
            learning=learning_200,
            targets=str(learning_context["target_id"]),
            db_path=learning_context["db_path"],
        )
        result = execute(args)
        assert result == 0

        # Verify it was stored as object
        with sqlite3.connect(learning_context["db_path"]) as conn:
            row = conn.execute(
                "SELECT metadata FROM tasks WHERE id = ?",
                (learning_context["source_id"],),
            ).fetchone()

        metadata = json.loads(row[0]) if row[0] else {}
        learning_obj = metadata["learnings"][0]
        assert learning_obj["text"] == learning_200

    def test_no_task_context_returns_not_found(self, db_path, monkeypatch, capsys):
        """Running outside worker session returns NOT_FOUND."""
        from formaltask.cli.commands import learning
        from formaltask.cli.exit_codes import ExitCode

        # Mock get_task_id_from_session to return None
        monkeypatch.setattr(learning, "get_task_id_from_session", lambda: None)

        args = Namespace(learning="Test insight", targets="1", db_path=db_path)
        result = learning.execute(args)

        assert result == ExitCode.NOT_FOUND

        # Verify error message
        captured = capsys.readouterr()
        assert "No task context. Run from worker session." in captured.err

    def test_multiple_learnings_append(self, learning_context):
        """Multiple calls append to list (second learning doesn't replace first)."""
        from formaltask.cli.commands.learning import execute

        # First learning
        args1 = Namespace(
            learning="First insight",
            targets=str(learning_context["target_id"]),
            db_path=learning_context["db_path"],
        )
        result1 = execute(args1)
        assert result1 == 0

        # Second learning
        args2 = Namespace(
            learning="Second insight",
            targets=str(learning_context["target_id"]),
            db_path=learning_context["db_path"],
        )
        result2 = execute(args2)
        assert result2 == 0

        # Verify both learnings present
        with sqlite3.connect(learning_context["db_path"]) as conn:
            row = conn.execute(
                "SELECT metadata FROM tasks WHERE id = ?",
                (learning_context["source_id"],),
            ).fetchone()

        metadata = json.loads(row[0])
        assert len(metadata["learnings"]) == 2
        assert metadata["learnings"][0]["text"] == "First insight"
        assert metadata["learnings"][1]["text"] == "Second insight"

    def test_task_not_found_returns_not_found(self, db_path, monkeypatch, capsys):
        """Invalid task_id returns NOT_FOUND."""
        from formaltask.cli.commands import learning
        from formaltask.cli.exit_codes import ExitCode

        # Mock get_task_id_from_session to return non-existent task
        monkeypatch.setattr(learning, "get_task_id_from_session", lambda: 99999)

        args = Namespace(learning="Test insight", targets="1", db_path=db_path)
        result = learning.execute(args)

        assert result == ExitCode.NOT_FOUND

        # Verify error message
        captured = capsys.readouterr()
        assert "99999" in captured.err and "not found" in captured.err.lower()

    def test_null_metadata_handled(self, learning_context):
        """Task with NULL metadata creates learnings array."""
        from formaltask.cli.commands.learning import execute

        # Explicitly set metadata to NULL
        with sqlite3.connect(learning_context["db_path"]) as conn:
            conn.execute(
                "UPDATE tasks SET metadata = NULL WHERE id = ?",
                (learning_context["source_id"],),
            )
            conn.commit()

        args = Namespace(
            learning="Fresh start",
            targets=str(learning_context["target_id"]),
            db_path=learning_context["db_path"],
        )
        result = execute(args)
        assert result == 0

        # Verify learning stored as object
        with sqlite3.connect(learning_context["db_path"]) as conn:
            row = conn.execute(
                "SELECT metadata FROM tasks WHERE id = ?",
                (learning_context["source_id"],),
            ).fetchone()

        metadata = json.loads(row[0])
        assert len(metadata["learnings"]) == 1
        assert metadata["learnings"][0]["text"] == "Fresh start"
        assert metadata["learnings"][0]["targets"] == [learning_context["target_id"]]

    def test_empty_learning_rejected(self, learning_context, capsys):
        """Empty learning returns VALIDATION_ERROR."""
        from formaltask.cli.commands.learning import execute
        from formaltask.cli.exit_codes import ExitCode

        args = Namespace(
            learning="",
            targets=str(learning_context["target_id"]),
            db_path=learning_context["db_path"],
        )
        result = execute(args)

        assert result == ExitCode.VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Learning cannot be empty" in captured.err

    def test_whitespace_only_learning_rejected(self, learning_context, capsys):
        """Whitespace-only learning returns VALIDATION_ERROR."""
        from formaltask.cli.commands.learning import execute
        from formaltask.cli.exit_codes import ExitCode

        args = Namespace(
            learning="   ",
            targets=str(learning_context["target_id"]),
            db_path=learning_context["db_path"],
        )
        result = execute(args)

        assert result == ExitCode.VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Learning cannot be empty" in captured.err


class TestTargetedLearnings:
    """Tests for targeted learnings with --for flag (Task #2672)."""

    def test_self_capture_without_for_flag(self, db_path, repo, monkeypatch):
        """ft learning "text" without --for captures for self (targets=[])."""
        from formaltask.cli.commands.learning import execute

        repo.create_epic("test-epic", "Test")
        task_id = repo.create_task("test-epic", "Task", "Desc", ["criterion"])

        monkeypatch.setenv("TASK_ID", str(task_id))

        # Learning text without --for = self-capture
        args = Namespace(learning="Self insight", targets=None, db_path=db_path)
        result = execute(args)

        assert result == 0

        # Verify stored with empty targets
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT metadata FROM tasks WHERE id = ?", (task_id,)).fetchone()
        metadata = json.loads(row[0])
        learning_obj = metadata["learnings"][0]
        assert learning_obj["text"] == "Self insight"
        assert learning_obj["targets"] == []

    def test_nonexistent_target_returns_not_found(self, db_path, repo, monkeypatch, capsys):
        """ft learning "text" --for 999 (non-existent task) returns NOT_FOUND."""
        from formaltask.cli.commands import learning
        from formaltask.cli.exit_codes import ExitCode

        repo.create_epic("test-epic", "Test")
        source_task_id = repo.create_task("test-epic", "Source task", "Desc", ["criterion"])

        monkeypatch.setenv("TASK_ID", str(source_task_id))

        # Target non-existent task
        args = Namespace(
            learning="Some insight",
            targets="99999",
            db_path=db_path,
        )
        result = learning.execute(args)

        assert result == ExitCode.NOT_FOUND
        captured = capsys.readouterr()
        assert "99999" in captured.err

    def test_self_reference_returns_validation_error(self, db_path, repo, monkeypatch, capsys):
        """ft learning "text" --for <self> returns VALIDATION_ERROR with 'cannot target self'."""
        from formaltask.cli.commands import learning
        from formaltask.cli.exit_codes import ExitCode

        repo.create_epic("test-epic", "Test")
        task_id = repo.create_task("test-epic", "Task", "Desc", ["criterion"])

        monkeypatch.setenv("TASK_ID", str(task_id))

        # Target self
        args = Namespace(
            learning="Some insight",
            targets=str(task_id),
            db_path=db_path,
        )
        result = learning.execute(args)

        assert result == ExitCode.VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "cannot target self" in captured.err.lower()

    def test_completed_task_returns_validation_error(self, db_path, repo, monkeypatch, capsys):
        """ft learning "text" --for <completed_task> returns VALIDATION_ERROR with 'already completed'."""
        from formaltask.cli.commands import learning
        from formaltask.cli.exit_codes import ExitCode
        from formaltask.utils.constants import TaskStatus

        repo.create_epic("test-epic", "Test")
        source_task_id = repo.create_task("test-epic", "Source task", "Desc", ["criterion"])
        target_task_id = repo.create_task("test-epic", "Target task", "Desc", ["criterion"])

        # Mark target task as completed
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (TaskStatus.COMPLETED.value, target_task_id),
            )
            conn.commit()

        monkeypatch.setenv("TASK_ID", str(source_task_id))

        args = Namespace(
            learning="Some insight",
            targets=str(target_task_id),
            db_path=db_path,
        )
        result = learning.execute(args)

        assert result == ExitCode.VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "already completed" in captured.err.lower()

    def test_different_epic_returns_validation_error(self, db_path, repo, monkeypatch, capsys):
        """Target in different epic returns VALIDATION_ERROR."""
        from formaltask.cli.commands import learning
        from formaltask.cli.exit_codes import ExitCode

        repo.create_epic("epic-1", "Epic 1")
        repo.create_epic("epic-2", "Epic 2")
        source_task_id = repo.create_task("epic-1", "Source task", "Desc", ["criterion"])
        target_task_id = repo.create_task("epic-2", "Target task", "Desc", ["criterion"])

        monkeypatch.setenv("TASK_ID", str(source_task_id))

        args = Namespace(
            learning="Some insight",
            targets=str(target_task_id),
            db_path=db_path,
        )
        result = learning.execute(args)

        assert result == ExitCode.VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "epic" in captured.err.lower()

    def test_multiple_targets_comma_separated(self, db_path, repo, monkeypatch):
        """--for 47,48 parses to [47, 48] and stores both targets."""
        from formaltask.cli.commands.learning import execute

        repo.create_epic("test-epic", "Test")
        source_task_id = repo.create_task("test-epic", "Source task", "Desc", ["criterion"])
        target_1_id = repo.create_task("test-epic", "Target 1", "Desc", ["criterion"])
        target_2_id = repo.create_task("test-epic", "Target 2", "Desc", ["criterion"])

        monkeypatch.setenv("TASK_ID", str(source_task_id))

        # Comma-separated targets
        args = Namespace(
            learning="Multi-target insight",
            targets=f"{target_1_id},{target_2_id}",
            db_path=db_path,
        )
        result = execute(args)

        assert result == 0

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT metadata FROM tasks WHERE id = ?",
                (source_task_id,),
            ).fetchone()

        metadata = json.loads(row[0])
        learning_obj = metadata["learnings"][0]
        assert sorted(learning_obj["targets"]) == sorted([target_1_id, target_2_id])

    def test_invalid_target_id_returns_validation_error(self, db_path, repo, monkeypatch, capsys):
        """Non-integer target ID returns VALIDATION_ERROR."""
        from formaltask.cli.commands import learning
        from formaltask.cli.exit_codes import ExitCode

        repo.create_epic("test-epic", "Test")
        task_id = repo.create_task("test-epic", "Task", "Desc", ["criterion"])

        monkeypatch.setenv("TASK_ID", str(task_id))

        # Invalid target ID
        args = Namespace(
            learning="Some insight",
            targets="abc",
            db_path=db_path,
        )
        result = learning.execute(args)

        assert result == ExitCode.VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "invalid" in captured.err.lower() or "integer" in captured.err.lower()

    def test_empty_targets_string_is_self_capture(self, db_path, repo, monkeypatch):
        """Empty target string is treated as self-capture (targets=[])."""
        from formaltask.cli.commands.learning import execute

        repo.create_epic("test-epic", "Test")
        task_id = repo.create_task("test-epic", "Task", "Desc", ["criterion"])

        monkeypatch.setenv("TASK_ID", str(task_id))

        # Empty targets string = self-capture
        args = Namespace(
            learning="Some insight",
            targets="",
            db_path=db_path,
        )
        result = execute(args)

        assert result == 0

        # Verify stored with empty targets
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT metadata FROM tasks WHERE id = ?", (task_id,)).fetchone()
        metadata = json.loads(row[0])
        assert metadata["learnings"][0]["targets"] == []
