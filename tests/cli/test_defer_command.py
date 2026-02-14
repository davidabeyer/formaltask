"""Tests for ft defer command (Task #2890).

The defer command creates new tasks from review findings with provenance tracking.
"""

import argparse

import pytest


class TestSetupParser:
    """Tests for setup_parser function."""

    def test_setup_parser_adds_file_positional(self):
        """setup_parser adds FILE positional argument."""
        from formaltask.cli.commands.defer import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)
        # Parse with required args
        args = parser.parse_args(["src/foo.py", "42", "--title", "Fix"])
        assert args.file == "src/foo.py"

    def test_setup_parser_adds_line_positional(self):
        """setup_parser adds LINE positional argument."""
        from formaltask.cli.commands.defer import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)
        args = parser.parse_args(["src/foo.py", "42", "--title", "Fix"])
        assert args.line == 42

    def test_setup_parser_adds_required_title(self):
        """setup_parser adds required --title flag."""
        from formaltask.cli.commands.defer import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)
        # Missing --title should raise
        with pytest.raises(SystemExit):
            parser.parse_args(["src/foo.py", "42"])

    def test_setup_parser_adds_task_type_with_default(self):
        """setup_parser adds --task-type with critique-gated default."""
        from formaltask.cli.commands.defer import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)
        args = parser.parse_args(["src/foo.py", "42", "--title", "Fix"])
        assert args.task_type == "critique-gated"


class TestExecute:
    """Tests for execute function."""

    def test_defer_creates_task_with_finding_ref(self, db_path, repo, tmp_path, monkeypatch):
        """ft defer src/foo.py 42 --title 'Fix' creates task with finding_ref metadata."""
        from formaltask.cli.commands.defer import execute

        # Create epic and test file
        repo.create_epic("test-epic", "Test epic")
        test_file = tmp_path / "src" / "foo.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# line content\n" * 50)

        # Mock worker context to return a source task id
        monkeypatch.setattr(
            "formaltask.cli.commands.defer.get_task_id_from_session",
            lambda: 1,
        )

        args = argparse.Namespace(
            file=str(test_file),
            line=42,
            title="Fix edge case",
            task_type="critique-gated",
            epic="test-epic",
            spawn=False,
            db_path=db_path,
        )

        result = execute(args)

        assert result == 0

        # Verify task was created with correct metadata
        from formaltask.tasks.crud import get_tasks

        tasks = get_tasks(db_path, "test-epic")
        assert len(tasks) == 1

        # Get full task to check metadata
        from formaltask.tasks.crud import get_task

        task = get_task(db_path, tasks[0]["id"])
        assert task is not None
        assert task["metadata"] is not None
        # finding_ref uses resolved path
        assert task["metadata"]["finding_ref"] == f"{test_file.resolve()}:42"

    def test_defer_critique_gated_writes_completion_rules(self, db_path, repo, tmp_path, monkeypatch):
        """ft defer --task-type critique-gated stores completion_rules in metadata."""
        import json

        from formaltask.cli.commands.defer import execute
        from formaltask.tasks.crud import get_task, get_tasks

        repo.create_epic("test-epic", "Test epic")
        test_file = tmp_path / "src" / "foo.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# line content\n" * 50)

        monkeypatch.setattr(
            "formaltask.cli.commands.defer.get_task_id_from_session",
            lambda: None,
        )

        args = argparse.Namespace(
            file=str(test_file),
            line=42,
            title="Fix edge case",
            task_type="critique-gated",
            epic="test-epic",
            spawn=False,
            db_path=db_path,
        )

        result = execute(args)
        assert result == 0

        tasks = get_tasks(db_path, "test-epic")
        task = get_task(db_path, tasks[0]["id"])
        metadata = task["metadata"]

        assert "completion_rules" in metadata
        rules = metadata["completion_rules"]
        assert len(rules) == 1
        assert "review_rounds.self-critique" in rules[0]["when"]
        assert rules[0]["priority"] == 1

    def test_defer_rejects_duplicate_finding_ref(self, db_path, repo, tmp_path, monkeypatch, capsys):
        """ft defer exits with ALREADY_EXISTS error when finding_ref already exists."""
        from formaltask.cli.commands.defer import execute
        from formaltask.cli.exit_codes import ExitCode

        # Create epic and test file
        repo.create_epic("test-epic", "Test epic")
        test_file = tmp_path / "src" / "foo.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# line content\n" * 50)

        # Mock worker context
        monkeypatch.setattr(
            "formaltask.cli.commands.defer.get_task_id_from_session",
            lambda: 1,
        )

        args = argparse.Namespace(
            file=str(test_file),
            line=42,
            title="Fix edge case",
            task_type="critique-gated",
            epic="test-epic",
            spawn=False,
            db_path=db_path,
        )

        # First call should succeed
        result1 = execute(args)
        assert result1 == 0

        # Second call with same file:line should fail
        args2 = argparse.Namespace(
            file=str(test_file),
            line=42,
            title="Another fix",
            task_type="critique-gated",
            epic="test-epic",
            spawn=False,
            db_path=db_path,
        )
        result2 = execute(args2)
        assert result2 == ExitCode.ALREADY_EXISTS.value

        # Check error message
        captured = capsys.readouterr()
        assert "already exists" in captured.err.lower()
