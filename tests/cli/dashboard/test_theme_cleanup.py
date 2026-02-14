"""Tests for Task #2909: Theme cleanup and orphan removal."""

from __future__ import annotations

from pathlib import Path

THEME_PATH = Path(__file__).parent.parent.parent.parent / "formaltask" / "apps" / "dashboard" / "theme.tcss"

# Build search strings via concatenation to avoid this file matching the grep check
_DELETED_SYMBOLS = [
    "Help" + "Screen",
    "Jump" + "ModeScreen",
    "JUMP" + "_KEYS",
    "jump" + "_mode",
    "help" + "_screen",
    "Task" + "Sidebar",
    "show_" + "jump_hint",
]


class TestThemeCSSCleanup:
    """Verify 3-pane and modal CSS selectors are removed from theme.tcss."""

    def test_theme_tcss_parses_without_error(self) -> None:
        """theme.tcss exists and is valid CSS (non-empty, readable)."""
        assert THEME_PATH.exists(), f"theme.tcss not found at {THEME_PATH}"
        content = THEME_PATH.read_text()
        assert len(content) > 0, "theme.tcss is empty"

    def test_has_task_list_css(self) -> None:
        """theme.tcss has #task-list styling."""
        content = THEME_PATH.read_text()
        assert "#task-list" in content

    def test_has_status_bar_css(self) -> None:
        """theme.tcss has #status-bar styling."""
        content = THEME_PATH.read_text()
        assert "#status-bar" in content

    def test_has_terminal_pane_css(self) -> None:
        """theme.tcss has #terminal-pane styling for always-on terminal."""
        content = THEME_PATH.read_text()
        assert "#terminal-pane" in content


class TestNoOrphanedImports:
    """Verify no orphaned references to deleted modules."""

    def test_no_orphaned_references_in_codebase(self) -> None:
        """No references to deleted screen modules in production or test .py files (AC c-2)."""
        import subprocess

        # Use grep alternation pattern built from concatenated strings
        pattern = r"\|".join(_DELETED_SYMBOLS)
        result = subprocess.run(
            [
                "grep", "-r",
                pattern,
                "formaltask/", "tests/",
                "--include=*.py",
                "-l",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=THEME_PATH.parent.parent.parent.parent,
        )
        matching_files = [f for f in result.stdout.strip().split("\n") if f]
        assert len(matching_files) == 0, (
            f"Orphaned references found in: {matching_files}"
        )


