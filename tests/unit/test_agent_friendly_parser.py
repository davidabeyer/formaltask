"""Tests for AgentFriendlyParser token-efficient CLI errors.

Acceptance criteria from Task #2292:
- pm nonexistent-cmd error output is less than 200 characters total
- Invalid command error includes fuzzy-matched suggestion (e.g., 'Did you mean: epic?')
- Error message includes 'Run: ft --help' hint
"""

import io
import sys


class TestAgentFriendlyParserErrorLength:
    """Test that error messages are concise (< 200 chars)."""

    def test_invalid_command_error_under_200_chars(self):
        """Invalid command error should be under 200 characters total."""
        from formaltask.cli.pm import main

        captured = io.StringIO()
        old_stderr, old_argv = sys.stderr, sys.argv
        sys.stderr = captured

        try:
            sys.argv = ["pm", "nonexistent-cmd"]
            exit_code = main()
        except SystemExit as e:
            exit_code = e.code
        finally:
            sys.stderr, sys.argv = old_stderr, old_argv

        error_output = captured.getvalue()
        assert len(error_output) < 200, (
            f"Error output is {len(error_output)} chars, expected < 200. Output: {error_output!r}"
        )
        assert exit_code == 2, "Should exit with code 2 for invalid command"


class TestAgentFriendlyParserFuzzyMatch:
    """Test fuzzy matching suggestions for invalid commands."""

    def test_close_match_suggests_epic(self):
        """Typing 'epci' should suggest 'epic'."""
        from formaltask.cli.pm import main

        captured = io.StringIO()
        old_stderr, old_argv = sys.stderr, sys.argv
        sys.stderr = captured

        try:
            sys.argv = ["pm", "epci"]
            main()
        except SystemExit:
            pass
        finally:
            sys.stderr, sys.argv = old_stderr, old_argv

        error_output = captured.getvalue()
        assert "Did you mean:" in error_output, (
            f"Expected fuzzy match suggestion. Output: {error_output!r}"
        )
        assert "epic" in error_output, (
            f"Expected 'epic' suggestion. Output: {error_output!r}"
        )

    def test_work_typo_suggests_work(self):
        """Typing 'wrok' should suggest 'work'."""
        from formaltask.cli.pm import main

        captured = io.StringIO()
        old_stderr, old_argv = sys.stderr, sys.argv
        sys.stderr = captured

        try:
            sys.argv = ["pm", "wrok"]
            main()
        except SystemExit:
            pass
        finally:
            sys.stderr, sys.argv = old_stderr, old_argv

        error_output = captured.getvalue()
        assert "Did you mean:" in error_output, (
            f"Expected fuzzy match suggestion for 'wrok'. Output: {error_output!r}"
        )
        assert "work" in error_output, f"Expected 'work' suggestion. Output: {error_output!r}"


class TestAgentFriendlyParserHelpHint:
    """Test that error messages include help hint."""

    def test_error_includes_help_hint(self):
        """Error messages should include 'Run: ft --help' hint."""
        from formaltask.cli.pm import main

        captured = io.StringIO()
        old_stderr, old_argv = sys.stderr, sys.argv
        sys.stderr = captured

        try:
            sys.argv = ["ft", "nonexistent-cmd"]
            main()
        except SystemExit:
            pass
        finally:
            sys.stderr, sys.argv = old_stderr, old_argv

        error_output = captured.getvalue()
        assert "Run: ft --help" in error_output, f"Expected help hint. Output: {error_output!r}"
