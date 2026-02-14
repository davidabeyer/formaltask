"""Integration tests for task_add with template support.

Tests that --spec-review flag applies the spec-review template metadata.
Uses FORMALTASK_TEMPLATES_DIR env var to point to temp templates directory.
"""

import json
import os
import sqlite3
import subprocess
import sys


def test_task_add_spec_review_applies_template_metadata(db_path, tmp_path):
    """--spec-review applies spec-review template (require_pr: false)."""
    # Setup: Create epic and spec-review template
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("myepic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create temp templates directory with spec-review template
    templates_dir = tmp_path / "task-templates"
    templates_dir.mkdir()
    spec_review_template = templates_dir / "spec-review.yaml"
    spec_review_template.write_text("require_pr: false\nrequired_reviews:\n  - spec-critique\n")

    # Set FORMALTASK_TEMPLATES_DIR env var for the subprocess
    env = os.environ.copy()
    env["FORMALTASK_TEMPLATES_DIR"] = str(templates_dir)

    # When: Running CLI with --spec-review flag and --dry-run
    # Note: --dry-run and --json are global flags (before subcommand), --db-path is subcommand flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "--json",
            "--dry-run",
            "task", "add",
            "myepic",
            "Test task",
            "Test description",
            "--criteria",
            "Test criterion",
            "--spec-review",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    # Then: Command should succeed and show metadata with require_pr: false
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # The dry-run output should show the merged metadata from the spec-review template
    output = json.loads(result.stdout)
    assert output["success"] is True
    assert output["data"]["dry_run"]["template"] == "spec-review"
    assert output["data"]["dry_run"]["metadata"]["require_pr"] is False
