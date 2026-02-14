#!/usr/bin/env python3
"""Integration tests for formaltask_db_guard hook.

This verifies the hook works with the JSON protocol used by Claude Code.
Tests run the actual hook as a subprocess to verify end-to-end behavior.
"""

import json
import os
import subprocess
import sys


class TestFormaltaskDbGuardHook:
    """Integration tests for the formaltask_db_guard PreToolUse hook."""

    def test_allows_non_formaltask_commands(self):
        """Hook should allow non-FormalTask commands without output."""
        hook_input = {"tool_name": "Bash", "tool_input": {"command": "git status"}}

        proc = subprocess.run(
            [sys.executable, "-m", "formaltask.validators.db_guard"],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
        )

        assert proc.returncode == 0, f"Expected 0, got {proc.returncode}. stderr: {proc.stderr}"
        assert proc.stdout.strip() == "", f"Expected no output, got: {proc.stdout}"

    def test_blocks_non_canonical_paths(self):
        """Hook should block non-canonical database paths with block decision."""
        hook_input = {
            "tool_name": "Bash",
            "tool_input": {
                "command": "python3 -m formaltask.cli.pm epic-list --db-path /tmp/bad.db"
            },
        }

        proc = subprocess.run(
            [sys.executable, "-m", "formaltask.validators.db_guard"],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
        )

        assert proc.returncode == 0, f"Expected 0, got {proc.returncode}"
        output = json.loads(proc.stdout)
        assert output["decision"] == "block"
        assert "canonical" in output["reason"].lower()

    def test_allows_canonical_paths(self):
        """Hook should allow canonical database paths without output."""
        # Use PROJECT_ROOT env var for portable canonical path
        project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
        canonical_path = os.path.join(project_root, ".claude", "formaltask.db")

        hook_input = {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"python3 -m formaltask.cli.pm epic-list --db-path {canonical_path}"
            },
        }

        proc = subprocess.run(
            [sys.executable, "-m", "formaltask.validators.db_guard"],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
        )

        assert proc.returncode == 0, f"Expected 0, got {proc.returncode}. stderr: {proc.stderr}"
        assert proc.stdout.strip() == "", f"Expected no output, got: {proc.stdout}"

    def test_allows_commands_without_db_path(self):
        """Hook should allow FormalTask commands without explicit db-path (uses default)."""
        hook_input = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m formaltask.cli.pm epic-list"},
        }

        proc = subprocess.run(
            [sys.executable, "-m", "formaltask.validators.db_guard"],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
        )

        assert proc.returncode == 0, f"Expected 0, got {proc.returncode}. stderr: {proc.stderr}"
        assert proc.stdout.strip() == "", f"Expected no output, got: {proc.stdout}"
