"""Test pm.py CLI integration for list commands."""

import subprocess

# Note: db_path fixture is provided by hooks/tests/conftest.py


def test_pm_epic_list_command_works(db_path):
    """
    RED: Test pm epic-list command invokes epic_list function.
    """
    # When: Running pm epic-list
    result = subprocess.run(
        ["python", "-m", "formaltask.cli.pm", "epic", "list", "--db-path", str(db_path)],
        capture_output=True,
        text=True,
    )

    # Then: Should succeed and show output
    assert result.returncode == 0
    assert (
        "EPIC" in result.stdout
        or "No epics found" in result.stdout
        or "master-adhoc" in result.stdout
    )


def test_pm_task_list_command_works(db_path):
    """
    RED: Test pm task-list command invokes task_list function.
    """
    # When: Running pm task-list
    result = subprocess.run(
        [
            "python",
            "-m",
            "formaltask.cli.pm",
            "task",
            "list",
            "master-adhoc",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Should succeed and show output
    assert result.returncode == 0
    assert "ID" in result.stdout or "No tasks found" in result.stdout
