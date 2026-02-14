"""Unit tests for task completion chaining logic (Task #2929).

Tests that _should_chain() reads the .task/chain signal file and
_chain_to_next() spawns dependent tasks from the completed task's branch.
"""

import json
from pathlib import Path
from unittest.mock import patch


def _create_epic_with_chain(db_path, *, num_tasks=2, depends_on=None):
    """Create an epic with tasks for chaining tests.

    Args:
        db_path: Database path.
        num_tasks: Number of tasks to create.
        depends_on: JSON string for depends_on field of task 2+.

    Returns:
        List of task IDs created.
    """
    from formaltask.db.connection import DatabaseConnection

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("chain-epic", "Test chaining", "2025-01-01T00:00:00Z"),
        )
        task_ids = []
        for i in range(num_tasks):
            dep = depends_on if i > 0 else None
            status = "completed" if i == 0 else "open"
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, position, status,
                   created_at, depends_on)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    "chain-epic",
                    f"Task {i + 1}",
                    f"Task {i + 1} desc",
                    i + 1,
                    status,
                    "2025-01-01T00:00:00Z",
                    dep,
                ),
            )
            task_ids.append(cursor.lastrowid)
        conn.commit()
        return task_ids


class TestShouldChain:
    """Tests for _should_chain() signal file detection."""

    def test_returns_true_when_chain_file_exists(self, tmp_path, monkeypatch):
        """_should_chain returns True and deletes file when .task/chain exists."""
        from formaltask.cli.commands.task_complete import _should_chain

        monkeypatch.chdir(tmp_path)
        chain_dir = tmp_path / ".task"
        chain_dir.mkdir()
        chain_file = chain_dir / "chain"
        chain_file.touch()

        assert _should_chain() is True
        assert not chain_file.exists(), "Chain file should be deleted after reading"

    def test_returns_false_when_no_chain_file(self, tmp_path, monkeypatch):
        """_should_chain returns False when .task/chain does not exist."""
        from formaltask.cli.commands.task_complete import _should_chain

        monkeypatch.chdir(tmp_path)

        assert _should_chain() is False

    def test_returns_false_on_delete_failure(self, tmp_path, monkeypatch):
        """_should_chain returns False if chain file can't be deleted."""
        from formaltask.cli.commands.task_complete import _should_chain

        monkeypatch.chdir(tmp_path)
        chain_dir = tmp_path / ".task"
        chain_dir.mkdir()
        chain_file = chain_dir / "chain"
        chain_file.touch()

        with patch.object(Path, "unlink", side_effect=OSError("permission denied")):
            assert _should_chain() is False


class TestChainToNext:
    """Tests for _chain_to_next() dependent task spawning."""

    def test_spawns_single_dep_task(self, db_path, capsys):
        """_chain_to_next spawns a task whose only dependency just completed."""
        from formaltask.cli.commands.task_complete import _chain_to_next

        task_ids = _create_epic_with_chain(
            db_path, num_tasks=2, depends_on=None,
        )
        parent_id = task_ids[0]
        child_id = task_ids[1]

        # Set depends_on for child task
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "UPDATE tasks SET depends_on = ? WHERE id = ?",
                (json.dumps([parent_id]), child_id),
            )
            conn.commit()

        with (
            patch(
                "formaltask.tasks.spawnability.get_spawnable_tasks",
                return_value=[child_id],
            ),
            patch(
                "formaltask.workers.spawner.spawn_worker",
            ) as mock_spawn,
        ):
            _chain_to_next(db_path, parent_id)

        mock_spawn.assert_called_once_with(
            child_id, db_path, skip_fetch=True, chain=True,
            base_branch=f"task-{parent_id}",
        )
        captured = capsys.readouterr()
        assert f"#{child_id}" in captured.out

    def test_skips_multi_dep_tasks(self, db_path, capsys):
        """_chain_to_next skips tasks with multiple dependencies."""
        from formaltask.cli.commands.task_complete import _chain_to_next

        task_ids = _create_epic_with_chain(db_path, num_tasks=3)
        parent_id = task_ids[0]
        other_dep_id = task_ids[1]
        child_id = task_ids[2]

        # Child depends on both parent and other
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "UPDATE tasks SET depends_on = ? WHERE id = ?",
                (json.dumps([parent_id, other_dep_id]), child_id),
            )
            conn.commit()

        with (
            patch(
                "formaltask.tasks.spawnability.get_spawnable_tasks",
                return_value=[child_id],
            ),
            patch(
                "formaltask.workers.spawner.spawn_worker",
            ) as mock_spawn,
        ):
            _chain_to_next(db_path, parent_id)

        mock_spawn.assert_not_called()
        captured = capsys.readouterr()
        assert "multiple dependencies" in captured.out

    def test_prints_chain_complete_when_no_candidates(self, db_path, capsys):
        """_chain_to_next prints 'Chain complete' when no tasks are chainable."""
        from formaltask.cli.commands.task_complete import _chain_to_next

        task_ids = _create_epic_with_chain(db_path, num_tasks=1)

        with patch(
            "formaltask.tasks.spawnability.get_spawnable_tasks",
            return_value=[],
        ):
            _chain_to_next(db_path, task_ids[0])

        captured = capsys.readouterr()
        assert "Chain complete" in captured.out
