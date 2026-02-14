"""Unit tests for statusline trimming.

Tests for formaltask.apps.dashboard.state module's trim_statusline function
that removes Claude Code statusline elements from tmux output.
"""

from hypothesis import given
from hypothesis import strategies as st


class TestTrimStatusline:
    """Tests for the trim_statusline function."""

    def test_trim_statusline_empty_input(self) -> None:
        """Empty input should return empty string."""
        from formaltask.apps.dashboard.state import trim_statusline

        result = trim_statusline("")
        assert result == ""

    def test_trim_statusline_no_divider_found(self) -> None:
        """Input with 5+ lines but no divider should return original."""
        from formaltask.apps.dashboard.state import trim_statusline

        original = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\n"
        result = trim_statusline(original)
        assert result == original

    def test_trim_statusline_short_input(self) -> None:
        """Input with < 5 lines should return original unchanged."""
        from formaltask.apps.dashboard.state import trim_statusline

        original = "line1\nline2\nline3"
        result = trim_statusline(original)
        assert result == original

    def test_trim_statusline_preserves_content(self) -> None:
        """Content before statusline should be preserved."""
        from formaltask.apps.dashboard.state import trim_statusline

        output = """Important output line 1
Important output line 2
Important output line 3
────────────────────────────────
> Try "some suggestion"
────────────────────────────────
┌ ~/.claude/worktrees/task-42
└ session: $0.50 │ total: $10.00"""

        result = trim_statusline(output)
        assert "Important output line 1" in result
        assert "Important output line 2" in result
        assert "Important output line 3" in result
        assert "session: $0.50" not in result

    def test_trim_statusline_divider_at_first_line(self) -> None:
        """Divider at first line should return empty string."""
        from formaltask.apps.dashboard.state import trim_statusline

        output = "────────────────────\nLine 2\nLine 3\nLine 4\nLine 5\n"
        result = trim_statusline(output)
        assert result == ""

    def test_trim_statusline_multiple_dividers(self) -> None:
        """Multiple dividers should trim from first divider (start of statusline block)."""
        from formaltask.apps.dashboard.state import trim_statusline

        output = """Line 1
────────────────────
Line 3
Line 4
────────────────────
statusline content"""
        result = trim_statusline(output)
        # Should keep everything BEFORE the first divider in statusline block
        # The first divider marks the start of statusline - everything after is removed
        assert "Line 1" in result
        assert "Line 3" not in result  # After first divider - removed
        assert "Line 4" not in result  # After first divider - removed
        assert "statusline content" not in result

    def test_trim_statusline_exactly_five_lines(self) -> None:
        """Exactly 5 lines should be processed (not short-circuited)."""
        from formaltask.apps.dashboard.state import trim_statusline

        output = "Line 1\nLine 2\nLine 3\n────────────────────\nstatusline"
        result = trim_statusline(output)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
        assert "statusline" not in result


class TestTrimStatuslineProperties:
    """Property-based tests for trim_statusline function."""

    @given(st.text())
    def test_trim_statusline_idempotent(self, text: str) -> None:
        """Trimming twice should equal trimming once."""
        from formaltask.apps.dashboard.state import trim_statusline

        once = trim_statusline(text)
        twice = trim_statusline(once)
        assert once == twice

    @given(st.text())
    def test_trim_statusline_never_longer(self, text: str) -> None:
        """Result should never be longer than input."""
        from formaltask.apps.dashboard.state import trim_statusline

        result = trim_statusline(text)
        assert len(result) <= len(text)
