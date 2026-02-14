"""Tests for --why flag in pm spawnable command."""

import argparse
import json
import sqlite3
from argparse import Namespace
from pathlib import Path


def test_setup_parser_adds_why_argument():
    """AC1: --why flag exists."""
    from formaltask.cli.commands.spawnable import setup_parser

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers().add_parser("spawnable")
    setup_parser(subparser)

    args = parser.parse_args(["spawnable", "--why", "42"])
    assert args.why == 42


def test_setup_parser_adds_complete_argument():
    """AC3: --complete flag exists."""
    from formaltask.cli.commands.spawnable import setup_parser

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers().add_parser("spawnable")
    setup_parser(subparser)

    args = parser.parse_args(["spawnable", "--complete"])
    assert args.complete is True


def test_why_shows_dependency_blockers(db_path, repo: Path, capsys):
    """AC2: --why shows blockers for blocked task."""
    from formaltask.cli.commands import spawnable

    repo.create_epic("test-epic", "Test Epic")

    # Create a dependency task (stays open)
    dep_id = repo.create_task("test-epic", "Dependency Task", "First task", ["c1"])

    # Create dependent task that depends on dep_id
    task_id = repo.create_task("test-epic", "Dependent Task", "Needs dep", ["c1"])
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET depends_on = ? WHERE id = ?",
            (json.dumps([dep_id]), task_id),
        )
        conn.commit()

    # Execute with --why flag
    args = Namespace(db_path=str(db_path), why=task_id, complete=False)
    result = spawnable.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    # --why mode: NOT the list view (Ready:/Blocked:), but specific task info
    assert "Ready:" not in captured.out, "--why should not show list view"
    # Should show "Task #X blocked:" header
    assert f"Task #{task_id}" in captured.out
    # Should show dependency blocker info
    assert f"#{dep_id}" in captured.out
    assert "incomplete" in captured.out.lower() or "wait" in captured.out.lower()


def test_why_shows_no_blockers_for_spawnable_task(db_path, repo: Path, monkeypatch, capsys):
    """--why shows no blockers for a task that can spawn."""
    from formaltask.cli.commands import spawnable

    # Mock worktree check to avoid detecting real worktrees
    monkeypatch.setattr(spawnable, "_worktree_exists", lambda task_id: "")

    repo.create_epic("test-epic", "Test Epic")
    task_id = repo.create_task("test-epic", "Spawnable Task", "No deps", ["c1"])

    args = Namespace(db_path=str(db_path), why=task_id, complete=False)
    result = spawnable.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    # --why mode: NOT the list view
    assert "Ready:" not in captured.out, "--why should not show list view"
    assert f"Task #{task_id}" in captured.out
    # Should indicate ready to spawn (no blockers)
    assert "ready" in captured.out.lower() or "no blocker" in captured.out.lower()


def test_backwards_compatible_no_flags(db_path, repo: Path, monkeypatch, capsys):
    """AC4: No flags = existing behavior (Ready/Blocked list)."""
    from formaltask.cli.commands import spawnable

    # Mock worktree check to avoid detecting real worktrees
    monkeypatch.setattr(spawnable, "_worktree_exists", lambda task_id: "")

    repo.create_epic("test-epic", "Test Epic")
    repo.create_task("test-epic", "My Task", "Desc", ["c1"])

    # Execute without --why flag
    args = Namespace(db_path=str(db_path), why=None, complete=False)
    result = spawnable.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    # Should show Ready: section (existing behavior)
    assert "Ready:" in captured.out or "No open tasks" in captured.out


def test_why_complete_shows_completion_blockers(db_path, repo: Path, monkeypatch, capsys):
    """--why with --complete shows completion blockers."""
    from formaltask.cli.commands import spawnable

    # Mock worktree check
    monkeypatch.setattr(spawnable, "_worktree_exists", lambda task_id: "")

    repo.create_epic("test-epic", "Test Epic")
    task_id = repo.create_task("test-epic", "In Progress Task", "Desc", ["c1"])

    # Put task in_progress (so completion check is relevant)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
        conn.commit()

    # Execute with --why --complete
    args = Namespace(db_path=str(db_path), why=task_id, complete=True)
    result = spawnable.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    # Should show completion blockers header
    assert f"Task #{task_id}" in captured.out
    assert "cannot complete" in captured.out.lower() or "complete" in captured.out.lower()
    # Should mention reviews or PR (common completion blockers)
    assert "review" in captured.out.lower() or "pr" in captured.out.lower()
