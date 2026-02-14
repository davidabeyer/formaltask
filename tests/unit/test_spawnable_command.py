"""Tests for pm spawnable command."""

from pathlib import Path


def test_spawnable_command_returns_task_spawn_info(db_path, repo: Path, monkeypatch):
    """Command returns list of TaskSpawnInfo objects with id, epic, title, blockers."""
    from formaltask.cli.commands import spawnable as spawnable_module
    from formaltask.cli.commands.spawnable import TaskSpawnInfo, spawnable

    # Mock worktree check to avoid detecting real worktrees
    monkeypatch.setattr(spawnable_module, "_worktree_exists", lambda task_id: "")
    repo.create_epic("test-epic", "Test")
    task_id = repo.create_task("test-epic", "My Task", "Desc", ["c1"])

    result = spawnable(str(db_path))

    assert len(result) == 1
    assert isinstance(result[0], TaskSpawnInfo)
    assert result[0].id == task_id
    assert result[0].epic_name == "test-epic"
    assert result[0].title == "My Task"
    assert result[0].blockers == []
    assert result[0].can_spawn is True


def test_execute_returns_int(db_path, repo: Path, monkeypatch):
    """execute() returns an integer exit code."""
    from formaltask.cli.commands import spawnable
    from formaltask.db import path as db_path_module

    monkeypatch.setattr(db_path_module, "get_db_path", lambda: db_path)
    repo.create_epic("test-epic", "Test")

    result = spawnable.execute(None)

    assert result == 0


def test_execute_prints_spawnable_tasks(db_path, repo: Path, monkeypatch, capsys):
    """execute() prints spawnable tasks with ID, epic, and title."""
    from formaltask.cli.commands import spawnable
    from formaltask.db import path as db_path_module

    monkeypatch.setattr(db_path_module, "get_db_path", lambda: db_path)
    # Mock worktree check to avoid detecting real worktrees
    monkeypatch.setattr(spawnable, "_worktree_exists", lambda task_id: "")
    repo.create_epic("test-epic", "Test")
    task_id = repo.create_task("test-epic", "My Task", "Desc", ["c1"])

    spawnable.execute(None)

    captured = capsys.readouterr()
    assert "Ready:" in captured.out
    assert str(task_id) in captured.out
    assert "test-epic" in captured.out
    assert "My Task" in captured.out


def test_execute_uses_db_path_from_args(db_path, repo: Path, capsys):
    """execute() uses db_path from args when provided."""
    from argparse import Namespace

    from formaltask.cli.commands import spawnable

    repo.create_epic("test-epic", "Test")
    task_id = repo.create_task("test-epic", "My Task", "Desc", ["c1"])

    # Pass db_path via args instead of monkeypatching
    args = Namespace(db_path=str(db_path))
    result = spawnable.execute(args)

    assert result == 0
    captured = capsys.readouterr()
    assert str(task_id) in captured.out


def test_spawnable_shows_incomplete_dependency_as_blocker(db_path, repo: Path):
    """Tasks with incomplete dependencies show dependency blocker."""
    import json
    import sqlite3

    from formaltask.cli.commands.spawnable import spawnable

    repo.create_epic("test-epic", "Test")

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

    result = spawnable(str(db_path))

    # Both tasks should be returned, but dependent task should have blocker
    task_ids = [t.id for t in result]
    assert dep_id in task_ids, "Dependency task should be spawnable"
    assert task_id in task_ids, "Dependent task should be in results"

    dependent_task = next(t for t in result if t.id == task_id)
    assert dependent_task.can_spawn is False
    assert len(dependent_task.blockers) == 1
    assert f"dep #{dep_id}" in dependent_task.blockers[0].reason


def test_spawnable_allows_completed_dependencies(db_path, repo: Path):
    """Tasks with completed dependencies have no blockers."""
    import json
    import sqlite3

    from formaltask.cli.commands.spawnable import spawnable

    repo.create_epic("test-epic", "Test")

    # Create a dependency task and complete it
    dep_id = repo.create_task("test-epic", "Dependency Task", "First task", ["c1"])
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status = 'completed' WHERE id = ?",
            (dep_id,),
        )
        conn.commit()

    # Create dependent task that depends on completed dep_id
    task_id = repo.create_task("test-epic", "Dependent Task", "Needs dep", ["c1"])
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET depends_on = ? WHERE id = ?",
            (json.dumps([dep_id]), task_id),
        )
        conn.commit()

    result = spawnable(str(db_path))

    # Dependent task should be spawnable (no blockers)
    task_ids = [t.id for t in result]
    assert task_id in task_ids

    dependent_task = next(t for t in result if t.id == task_id)
    assert dependent_task.can_spawn is True
    assert dependent_task.blockers == []


def test_execute_rejects_symlink_db_path(tmp_path: Path, capsys):
    """execute() rejects symlink --db-path for security (Task #1965)."""
    from argparse import Namespace

    from formaltask.cli.commands import spawnable

    # Create real db and symlink to it
    real_db = tmp_path / "real.db"
    real_db.touch()
    symlink_db = tmp_path / "link.db"
    symlink_db.symlink_to(real_db)

    args = Namespace(db_path=str(symlink_db))
    result = spawnable.execute(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "symlink" in captured.out.lower()


def test_spawnable_allows_completed_cross_epic_dependencies(db_path, repo: Path):
    """Tasks with COMPLETED cross-epic dependencies have no blockers (Task #2122 fix).

    A task depending on a completed task from a different epic SHOULD be
    spawnable, since the dependency work is done.
    """
    import json
    import sqlite3

    from formaltask.cli.commands.spawnable import spawnable

    # Create two epics
    repo.create_epic("epic-a", "Epic A")
    repo.create_epic("epic-b", "Epic B")

    # Create a task in epic-a (dependency)
    dep_task_id = repo.create_task("epic-a", "Dependency Task", "In epic A", ["c1"])

    # Complete the dependency task
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status = 'completed' WHERE id = ?",
            (dep_task_id,),
        )
        conn.commit()

    # Create task in epic-b that depends on task in epic-a (cross-epic dependency)
    task_id = repo.create_task("epic-b", "Cross Epic Task", "Depends on epic A", ["c1"])
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET depends_on = ? WHERE id = ?",
            (json.dumps([dep_task_id]), task_id),
        )
        conn.commit()

    result = spawnable(str(db_path))

    task_ids = [t.id for t in result]
    assert task_id in task_ids, (
        f"Task #{task_id} should be spawnable since cross-epic dep #{dep_task_id} is completed"
    )

    cross_epic_task = next(t for t in result if t.id == task_id)
    assert cross_epic_task.can_spawn is True


def test_execute_shows_blocked_tasks_with_reasons(db_path, repo: Path, monkeypatch, capsys):
    """execute() shows blocked tasks with their blocker reasons."""
    import json
    import sqlite3
    from argparse import Namespace

    from formaltask.cli.commands import spawnable
    from formaltask.db import path as db_path_module

    monkeypatch.setattr(db_path_module, "get_db_path", lambda: db_path)
    # Mock worktree check to avoid detecting real worktrees
    monkeypatch.setattr(spawnable, "_worktree_exists", lambda task_id: "")
    repo.create_epic("test-epic", "Test")

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

    args = Namespace(db_path=str(db_path))
    spawnable.execute(args)

    captured = capsys.readouterr()
    assert "Ready:" in captured.out
    assert "Blocked:" in captured.out
    assert str(task_id) in captured.out
    assert f"dep #{dep_id}" in captured.out  # Blocker reason


def test_spawnable_returns_empty_list_when_no_open_tasks(db_path, repo: Path):
    """spawnable() returns empty list when no open tasks exist."""
    from formaltask.cli.commands.spawnable import spawnable

    repo.create_epic("test-epic", "Test")

    result = spawnable(str(db_path))

    assert result == []


def test_execute_prints_no_open_tasks_message(db_path, repo: Path, monkeypatch, capsys):
    """execute() prints 'No open tasks' when none exist."""
    from formaltask.cli.commands import spawnable
    from formaltask.db import path as db_path_module

    monkeypatch.setattr(db_path_module, "get_db_path", lambda: db_path)
    repo.create_epic("test-epic", "Test")

    spawnable.execute(None)

    captured = capsys.readouterr()
    assert "No open tasks" in captured.out
