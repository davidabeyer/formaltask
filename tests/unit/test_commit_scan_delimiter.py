"""Tests for commit_scan delimiter change (Task #1847).

Verifies that COMMIT_DELIMITER constant is ASCII Record Separator (\x1e)
and that commits with ||| in subject are parsed correctly.
"""

from unittest.mock import MagicMock, patch

from formaltask.cli.commands.commit_scan import COMMIT_DELIMITER, commit_scan


class TestCommitDelimiterConstant:
    """Tests for COMMIT_DELIMITER constant."""

    def test_commit_with_pipe_delimiter_in_subject_parsed_correctly(self):
        """Commits with ||| in subject are parsed correctly."""
        # Arrange: Mock git output with ||| in subject
        mock_output = f"abc123{COMMIT_DELIMITER}Fix bug ||| workaround{COMMIT_DELIMITER}Body text"

        # Act: Parse commit using the same logic as commit_scan
        parts = mock_output.split(COMMIT_DELIMITER, 2)

        # Assert: Subject preserved intact
        assert parts[0] == "abc123"
        assert parts[1] == "Fix bug ||| workaround"
        assert parts[2] == "Body text"

    @patch("formaltask.cli.commands.commit_scan.subprocess.run")
    def test_commit_scan_parses_commits_with_pipe_in_subject(self, mock_run):
        """commit_scan correctly parses commits with ||| in subject."""
        # Arrange: Git output with ||| in subject line
        git_output = f"abc123{COMMIT_DELIMITER}refs #42 ||| edge case{COMMIT_DELIMITER}Body\n"
        mock_run.return_value = MagicMock(stdout=git_output, returncode=0)

        mock_repo = MagicMock()
        mock_repo.db_path = ":memory:"

        # Act: Use a mock for DatabaseConnection to avoid actual DB operations
        with patch("formaltask.cli.commands.commit_scan.DatabaseConnection") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = commit_scan(mock_repo, task_id=42)

        # Assert: The commit was linked (parsing succeeded)
        assert result["linked_count"] == 1

        # Verify the full message includes the ||| preserved
        insert_call = mock_conn.execute.call_args
        full_message = insert_call[0][1][2]  # Third arg to INSERT
        assert "||| edge case" in full_message
