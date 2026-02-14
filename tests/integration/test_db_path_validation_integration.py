"""Integration tests for --db-path validation across all CLI commands (Task #1965).

Tests that all CLI commands properly reject symlink --db-path arguments.
"""

from argparse import Namespace
from pathlib import Path

import pytest

# Commands that need validation, with minimal required args for their execute()
# Task #2646: Removed task_start, pr_create, ready_tasks, epic_start, parallel_start (deleted)
# Task #2649: Removed epic_merge (deleted)
# Cleanup: Removed review_skip, review_retry, review_status, task_deps, task_search (deleted)
COMMANDS_WITH_DB_PATH = [
    (
        "epic_review",
        {
            "epic_name": "test",
            "all_epics": False,
            "json": False,
            "preflight": False,
            "dry_run": False,
        },
    ),
    ("commit_scan", {"task_id": None, "since": None, "json": False, "repo_path": None}),
    ("task_list", {"epic_name": "test", "status": None, "json": False}),
    ("epic_health", {"epic_name": "test", "json": False}),
    (
        "task_complete",
        {
            "task_id": 1,
            "skip_review": False,
            "no_evidence": False,
            "completion_evidence": None,
            "json": False,
            "preflight": False,
            "dry_run": False,
        },
    ),
    ("review_store", {"review_json": "{}", "json": False}),
    (
        "task_cancel",
        {
            "task_id": "1",
            "force": False,
            "reason": "This is a valid cancellation reason",
            "json": False,
            "preflight": False,
            "dry_run": False,
        },
    ),
    ("spawn", {"task_ids": [1], "fresh": False, "json": False}),
    (
        "epic_create",
        {
            "epic_name": "test",
            "description": "test",
            "json": False,
            "preflight": False,
            "dry_run": False,
        },
    ),
    (
        "task_defer",
        {
            "task_id": 1,
            "reason": "This is a valid defer reason with enough characters",
            "json": False,
        },
    ),
    ("commit_link", {"task_id": 1, "commit_hash": "abc123", "json": False}),
    (
        "task_update",
        {
            "task_id": 1,
            "title": "New title",
            "description": None,
            "add_criteria": None,
            "remove_criteria": None,
            "reset_status": False,
            "json": False,
        },
    ),
    ("epic_list", {"archived": False, "json": False}),
    (
        "epic_decompose",
        {"epic_name": "test", "epic_file": "/nonexistent/epic.md", "force": False, "json": False},
    ),
    ("spawnable", {"epic_name": None, "json": False}),
    (
        "epic_close",
        {
            "epic_name": "test",
            "force": False,
            "projects_dir": None,
            "preflight": False,
            "dry_run": False,
            "json": False,
        },
    ),
]


@pytest.mark.parametrize("command_name,extra_args", COMMANDS_WITH_DB_PATH)
def test_command_rejects_symlink_db_path(
    tmp_path: Path, command_name: str, extra_args: dict, capsys
):
    """All CLI commands with --db-path should reject symlinks for security (Task #1965).

    Commands without validation will either:
    - Crash with database/operational errors (validation missing)
    - Return 1 with 'symlink' in output (validation present)
    """
    import importlib

    # Create real db and symlink to it
    real_db = tmp_path / "real.db"
    real_db.touch()
    symlink_db = tmp_path / "link.db"
    symlink_db.symlink_to(real_db)

    # Import the command module
    module = importlib.import_module(f"formaltask.cli.commands.{command_name}")

    # Create args with symlink db_path
    args = Namespace(db_path=str(symlink_db), **extra_args)

    # Try to execute - if validation is missing, this may raise exceptions
    try:
        result = module.execute(args)
    except Exception as e:
        # If execute() crashes, validation is definitely missing
        pytest.fail(
            f"{command_name} crashed without validating symlink db_path: {type(e).__name__}: {e}"
        )

    # Should return error code (1) and mention symlink
    assert result == 1, f"{command_name} should return 1 for symlink db_path, got {result}"
    captured = capsys.readouterr()
    output = (captured.out + captured.err).lower()
    assert "symlink" in output, f"{command_name} should mention 'symlink' in error message"
