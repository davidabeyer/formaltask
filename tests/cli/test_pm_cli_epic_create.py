"""Test pm-epic-create CLI integration."""

import subprocess

# Note: db_path fixture is provided by hooks/tests/conftest.py


def test_pm_epic_create_command_works(db_path):
    """
    RED: Test pm epic-create command invokes epic_create function.
    """
    # When: Running pm epic-create
    result = subprocess.run(
        [
            "python",
            "-m",
            "formaltask.cli.pm",
            "epic", "create",
            "cli-test-epic",
            "Test description",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Should succeed and show output
    assert result.returncode == 0
    assert "✓ Created epic: cli-test-epic" in result.stdout
