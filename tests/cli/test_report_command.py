"""Tests for ft work report command.

Workers use this to report infrastructure problems (CI broken, etc.)
and create fix tasks for other workers, without blocking themselves.
"""

import argparse

import pytest


class TestSetupParser:
    """Tests for setup_parser function."""

    def test_setup_parser_adds_title_positional(self):
        """setup_parser adds title positional argument."""
        from formaltask.cli.commands.report import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)
        args = parser.parse_args(["Fix CI: pytest failures"])
        assert args.title == "Fix CI: pytest failures"

    def test_setup_parser_adds_optional_description(self):
        """setup_parser adds optional --description flag."""
        from formaltask.cli.commands.report import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)
        args = parser.parse_args(["Fix CI", "--description", "Master branch tests fail"])
        assert args.description == "Master branch tests fail"

    def test_setup_parser_title_is_required(self):
        """setup_parser requires title positional argument."""
        from formaltask.cli.commands.report import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestExecute:
    """Tests for execute function."""

    def test_report_creates_blocker_task(self, db_path, repo, monkeypatch):
        """ft work report creates task with task_type=blocker."""
        from formaltask.cli.commands.report import execute
        from formaltask.tasks.crud import get_task, get_tasks

        repo.create_epic("test-epic", "Test epic")
        source_id = repo.create_task("test-epic", "Original", "Desc", ["c1"])

        # Mock worker context
        monkeypatch.setattr(
            "formaltask.cli.commands.report.get_task_id_from_session",
            lambda: source_id,
        )

        args = argparse.Namespace(
            title="Fix CI: pytest failures",
            description="Master branch tests fail in test_auth",
            epic=None,
            db_path=db_path,
        )

        result = execute(args)
        assert result == 0

        tasks = get_tasks(db_path, "test-epic")
        # Original task + new blocker
        blocker = [t for t in tasks if t["title"] == "Fix CI: pytest failures"]
        assert len(blocker) == 1

        task = get_task(db_path, blocker[0]["id"])
        assert task["metadata"]["task_type"] == "blocker"
        assert task["metadata"]["source_task_id"] == source_id

    def test_report_sets_self_critique_review(self, db_path, repo, monkeypatch):
        """ft work report sets required_reviews to self-critique."""
        from formaltask.cli.commands.report import execute
        from formaltask.tasks.crud import get_task, get_tasks

        repo.create_epic("test-epic", "Test epic")
        source_id = repo.create_task("test-epic", "Original", "Desc", ["c1"])

        monkeypatch.setattr(
            "formaltask.cli.commands.report.get_task_id_from_session",
            lambda: source_id,
        )

        args = argparse.Namespace(
            title="Fix CI",
            description=None,
            epic=None,
            db_path=db_path,
        )

        execute(args)

        tasks = get_tasks(db_path, "test-epic")
        blocker = [t for t in tasks if t["title"] == "Fix CI"][0]
        task = get_task(db_path, blocker["id"])
        assert "self-critique" in task["metadata"]["required_reviews"]

    def test_report_deduplicates_open_blockers(self, db_path, repo, monkeypatch, capsys):
        """Second ft work report for same epic returns existing task instead of creating duplicate."""
        from formaltask.cli.commands.report import execute
        from formaltask.tasks.crud import get_tasks

        repo.create_epic("test-epic", "Test epic")
        source_id = repo.create_task("test-epic", "Original", "Desc", ["c1"])

        monkeypatch.setattr(
            "formaltask.cli.commands.report.get_task_id_from_session",
            lambda: source_id,
        )

        args1 = argparse.Namespace(
            title="Fix CI: pytest failures",
            description="Tests fail",
            epic=None,
            db_path=db_path,
        )
        result1 = execute(args1)
        assert result1 == 0

        # Second report for same epic — should dedup
        args2 = argparse.Namespace(
            title="Fix CI: auth tests broken",
            description="Different description",
            epic=None,
            db_path=db_path,
        )
        result2 = execute(args2)
        assert result2 == 0  # Not an error — just informs

        captured = capsys.readouterr()
        assert "already exists" in captured.out.lower()

        # Only one blocker task created
        tasks = get_tasks(db_path, "test-epic")
        blockers = [t for t in tasks if t["title"].startswith("Fix CI")]
        assert len(blockers) == 1

    def test_report_requires_worker_context(self, db_path, monkeypatch, capsys):
        """ft work report fails without worker context."""
        from formaltask.cli.commands.report import execute

        monkeypatch.setattr(
            "formaltask.cli.commands.report.get_task_id_from_session",
            lambda: None,
        )

        args = argparse.Namespace(
            title="Fix CI",
            description=None,
            epic=None,
            db_path=db_path,
        )

        result = execute(args)
        assert result != 0

        captured = capsys.readouterr()
        assert "worker" in captured.err.lower() or "task context" in captured.err.lower()

    def test_report_rejects_empty_title(self, db_path, repo, monkeypatch, capsys):
        """ft work report rejects empty title."""
        from formaltask.cli.commands.report import execute

        repo.create_epic("test-epic", "Test epic")
        source_id = repo.create_task("test-epic", "Original", "Desc", ["c1"])

        monkeypatch.setattr(
            "formaltask.cli.commands.report.get_task_id_from_session",
            lambda: source_id,
        )

        args = argparse.Namespace(
            title="   ",
            description=None,
            epic=None,
            db_path=db_path,
        )

        result = execute(args)
        assert result != 0

    def test_report_respects_rate_limit(self, db_path, repo, monkeypatch, capsys):
        """ft work report enforces max 3 tasks per source task."""
        from formaltask.cli.commands.report import execute
        from formaltask.tasks.crud import create_task

        repo.create_epic("test-epic", "Test epic")
        source_id = repo.create_task("test-epic", "Original", "Desc", ["c1"])

        monkeypatch.setattr(
            "formaltask.cli.commands.report.get_task_id_from_session",
            lambda: source_id,
        )

        # Pre-create 3 tasks with source_task_id pointing to our source
        for i in range(3):
            create_task(
                db_path=db_path,
                epic_name="test-epic",
                title=f"Existing {i}",
                description="Pre-existing",
                criteria=["c1"],
                metadata={"source_task_id": source_id, "task_type": "critique-gated"},
            )

        args = argparse.Namespace(
            title="Fix CI",
            description=None,
            epic=None,
            db_path=db_path,
        )

        result = execute(args)
        assert result != 0

        captured = capsys.readouterr()
        assert "max" in captured.err.lower() or "limit" in captured.err.lower()
