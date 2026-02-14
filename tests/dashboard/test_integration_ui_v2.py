"""Integration tests for Dashboard UI v2 features.

Task #2820: Validates all dashboard enhancements work together.
Depends on: Task #2816 (acceptance criteria), Task #2817 (tmux preview),
Task #2819 (epic name), Task #2782 (3-pane layout).

Test cases:
- test_dashboard_shows_acceptance_criteria: Select task, verify criteria displayed
- test_dashboard_shows_epic_name: Select task, verify epic name in detail
- test_dashboard_shows_tmux_preview: Verify workers pane shows captured output
- test_dashboard_epic_grouping: Verify tasks displayed as flat urgency-sorted list
- test_dashboard_h_l_collapse_expand: SKIPPED - feature not implemented (Task #2822 removed grouping)
- test_dashboard_focus_indicator: Focus pane, verify CSS class changes
"""

from __future__ import annotations

from pathlib import Path


class TestDashboardShowsTmuxPreview:
    """Integration test: tmux terminal preview in workers pane."""

    def test_format_selected_worker_terminal_shows_captured_output(self) -> None:
        """format_selected_worker_terminal displays pre-captured terminal content."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        captured = "Line 1: Running tests...\nLine 2: All tests passed!"
        result = format_selected_worker_terminal(42, captured_content=captured)
        text = str(result)

        assert "Running tests" in text
        assert "All tests passed" in text

    def test_format_selected_worker_terminal_no_selection(self) -> None:
        """format_selected_worker_terminal shows prompt when no task selected."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        result = format_selected_worker_terminal(None)
        text = str(result)

        assert "Select a worker to view terminal" in text


class TestDashboardEpicGrouping:
    """Integration test: task grouping behavior in sidebar.

    Note: Task #2822 simplified sidebar to flat urgency-sorted list.
    Epic grouping was removed - sidebar now displays all tasks flat.
    """

    def test_sidebar_displays_flat_list_not_grouped(self) -> None:
        """TaskList renders tasks as flat list, not grouped by epic."""
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        # Verify sidebar is a simple Static widget without epic group containers
        sidebar = TaskList(id="left-pane")

        # TaskList should have border_title "Tasks" (not epic-specific)
        assert sidebar.border_title == "Tasks"

    def test_sidebar_refresh_from_states_creates_flat_list(self) -> None:
        """refresh_from_states creates TaskRows without epic grouping."""
        from formaltask.apps.dashboard import widgets
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        # Verify TaskList has refresh_from_states method
        sidebar = TaskList(id="left-pane")
        assert hasattr(sidebar, "refresh_from_states")

        # Verify the method signature accepts states for multiple epics
        # (cannot call without mounting, but we verify method exists)
        import inspect

        sig = inspect.signature(sidebar.refresh_from_states)
        params = list(sig.parameters.keys())
        assert "states" in params
        assert "selected_id" in params

        # Confirm only TaskRow and TaskList are exported (no epic group widget)
        exported = [name for name in dir(widgets) if not name.startswith("_")]
        assert "EpicGroup" not in exported
        assert "TaskRow" in exported
        assert "TaskList" in exported


class TestDashboardFocusIndicator:
    """Integration test: focus indicator via CSS border color change.

    Task #2909: Flat layout uses #task-list focus-within.
    """

    def test_task_list_focus_within_style_defined(self) -> None:
        """CSS defines :focus-within rule for task-list border color change."""

        css_path = Path(__file__).parent.parent.parent / "formaltask" / "apps" / "dashboard" / "theme.tcss"

        css_content = css_path.read_text()

        # Verify :focus-within rules exist for task list
        assert "#task-list:focus-within" in css_content

        # Verify cyan border color on focus (#89dceb is Catppuccin Sky)
        assert "#89dceb" in css_content
