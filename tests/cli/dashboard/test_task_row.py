"""Tests for TaskRow widget."""

import pytest
from rich.text import Text


def test_task_row_renders_id_and_status() -> None:
    """TaskRow.render() includes task_id and status indicator."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=123,
        title="Test task",
        status="running",
        phase="implementing",
        elapsed_seconds=120,
    )
    row = TaskRow(data)
    result = row.render()

    # Should return a Text object
    assert isinstance(result, Text)
    # Should contain the task ID (not full title - detail shown in right pane)
    plain_text = result.plain
    assert "#123" in plain_text
    # Should contain elapsed time (2m for 120 seconds)
    assert "2m" in plain_text


def test_task_row_renders_phase_badge() -> None:
    """Running tasks show phase badge in render output."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=42,
        title="Running task",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
    )
    row = TaskRow(data)
    result = row.render()

    # Should have phase badge "IMPL" for implementing phase
    plain = result.plain
    assert "IMPL" in plain


def test_task_row_render_includes_phase_badge() -> None:
    """render() includes phase badge for the current phase."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Test",
        status="error",
        phase="blocked",
        elapsed_seconds=60,
    )
    row = TaskRow(data)
    result = row.render()

    # The phase badge "STOP" should appear for blocked phase
    assert "STOP" in result.plain


def test_task_row_render_right_aligns_time_and_badge() -> None:
    """render() right-aligns time and phase badge with task ID on left.

    Layout should be: #id...    badge time
    With padding between task ID and right-aligned badge+time.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Short title",
        status="idle",
        phase="done",
        elapsed_seconds=60,
    )
    row = TaskRow(data)
    result = row.render()

    plain = result.plain
    # Find positions of task ID end and time start
    id_end = plain.find("#1") + len("#1")
    time_pos = plain.find("1m")

    # There should be multiple spaces (>= 2) between task ID and time
    gap = time_pos - id_end
    assert gap >= 2, f"Expected padding gap >= 2, got {gap}. Output: '{plain}'"


def test_task_row_render_truncates_long_title() -> None:
    """render() truncates long titles to fit within row width."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    long_title = "A" * 80
    data = TaskRowData(
        task_id=2815,
        title=long_title,
        status="idle",
        phase="done",
        elapsed_seconds=60,
    )
    row = TaskRow(data)
    result = row.render()

    plain = result.plain
    assert "#2815" in plain
    # Title should be truncated (not all 80 A's)
    assert plain.count("A") < 80


# ===== Tests for Task #2695: Apply state colors to TaskRow sidebar items =====


def test_task_row_running_applies_green_style() -> None:
    """Running tasks render with green style (#a6e3a1).

    Task #2695: Apply STATE_STYLES to TaskRow items.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Running task",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
    )
    row = TaskRow(data)
    result = row.render()

    # Check that the Text object has style spans containing green color
    # The title portion should have the green style applied
    assert len(result.spans) > 0, "Text should have style spans applied"
    # Find span covering the title text
    title_span = result.spans[0]  # First span should be the styled title
    assert "#a6e3a1" in str(title_span.style).lower(), (
        f"Running task should have green (#a6e3a1) style, got: {title_span.style}"
    )


def test_task_row_unknown_status_applies_fallback_style() -> None:
    """Unknown status uses fallback dim gray style.

    Task #2695: Edge case - unknown status should use fallback.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Unknown task",
        status="some_unknown_status",
        phase="unknown",
        elapsed_seconds=60,
    )
    row = TaskRow(data)
    result = row.render()

    # Should apply fallback style
    assert len(result.spans) > 0, "Text should have style spans applied"
    title_span = result.spans[0]
    style_str = str(title_span.style).lower()
    assert "#9399b2" in style_str or "dim" in style_str, (
        f"Unknown status should use fallback dim gray style, got: {title_span.style}"
    )


# ===== Tests for Task #2771: Add blocked_question to TaskRow =====


@pytest.mark.xfail(reason="TDD Red phase: Task #2771 render() doesn't show blocked_question yet")
def test_task_row_renders_blocked_question_with_tree_prefix() -> None:
    """TaskRow renders blocked question below title with tree-style prefix.

    Task #2771: Display format:
        Add OAuth2 login flow         STOP  12m
        └─ "Which OAuth provider?"
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=42,
        title="Add OAuth2 login flow",
        status="error",
        phase="blocked",
        elapsed_seconds=720,
        blocked_question="Which OAuth provider should I use?",
    )
    row = TaskRow(data)
    result = row.render()

    plain = result.plain
    # Should contain tree-style prefix
    assert "└─" in plain
    # Should contain the question (possibly truncated)
    assert "Which OAuth provider" in plain


def test_task_row_does_not_render_question_line_when_none() -> None:
    """TaskRow doesn't render extra line when blocked_question is None.

    Task #2771: No question line for non-blocked tasks.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Regular task",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
        blocked_question=None,
    )
    row = TaskRow(data)
    result = row.render()

    plain = result.plain
    # Should NOT contain tree-style prefix
    assert "└─" not in plain


def test_task_row_truncates_long_blocked_question() -> None:
    """TaskRow truncates very long blocked questions to fit row width.

    Task #2771: Questions shouldn't overflow row width.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    long_question = "A" * 100  # Longer than row width
    data = TaskRowData(
        task_id=1,
        title="Task",
        status="error",
        phase="blocked",
        elapsed_seconds=60,
        blocked_question=long_question,
    )
    row = TaskRow(data)
    result = row.render()

    # Should be truncated with ellipsis
    plain = result.plain
    lines = plain.split("\n")
    # Each line should respect default render width (40)
    for line in lines:
        assert len(line) <= 40, f"Line exceeds render width: '{line}'"


# ===== Tests for Task #2784: update_from_state for differential updates =====


def test_task_row_update_from_state_updates_data() -> None:
    """update_from_state() should update the row's data with new state.

    Task #2784: The method should update TaskRowData without remounting.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    # Create initial row
    data = TaskRowData(
        task_id=42,
        title="Old Title",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
    )
    row = TaskRow(data)

    # Create new state dict
    new_state = TaskRowData(
        task_id=42,
        title="New Title",
        status="error",
        phase="blocked",
        elapsed_seconds=120,
        blocked_question="Need help with auth",
    )

    # Update the row
    row.update_from_state(new_state)

    # Data should be updated
    assert row.data.title == "New Title"
    assert row.data.status == "error"
    assert row.data.phase == "blocked"
    assert row.data.elapsed_seconds == 120
    assert row.data.blocked_question == "Need help with auth"


def test_task_row_update_from_state_calls_refresh() -> None:
    """update_from_state() should call refresh() to update display.

    Task #2784: After updating data, the widget needs to refresh its render.
    """
    from unittest.mock import patch

    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=42,
        title="Test",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
    )
    row = TaskRow(data)

    new_state = TaskRowData(
        task_id=42,
        title="Updated",
        status="idle",
        phase="done",
        elapsed_seconds=120,
    )

    with patch.object(row, "refresh") as mock_refresh:
        row.update_from_state(new_state)
        mock_refresh.assert_called_once()


def test_task_row_update_from_state_preserves_task_id() -> None:
    """update_from_state() should preserve the task_id from new state.

    Task #2784: task_id in the new state should match the row.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=42,
        title="Original",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
    )
    row = TaskRow(data)

    new_state = TaskRowData(
        task_id=42,
        title="Updated",
        status="idle",
        phase="done",
        elapsed_seconds=180,
    )

    row.update_from_state(new_state)

    assert row.data.task_id == 42


# ===== Tests for Task #2810: Stale worker visual indicator =====


def test_task_row_data_has_is_stale_field() -> None:
    """TaskRowData should have is_stale field for visual indication.

    Task #2810: Need to pass staleness to TaskRow for visual styling.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRowData

    # Should be able to create with is_stale
    data = TaskRowData(
        task_id=1,
        title="Task",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
        is_stale=True,
    )
    assert data.is_stale is True


def test_task_row_data_is_stale_defaults_to_false() -> None:
    """TaskRowData.is_stale should default to False.

    Task #2810: Non-stale workers should be the default.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Task",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
    )
    assert data.is_stale is False


def test_task_row_stale_worker_has_dim_style() -> None:
    """Stale running worker should render with dim style.

    Task #2810: Stale workers display dim style as visual indicator.
    """
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Stale running task",
        status="running",
        phase="implementing",
        elapsed_seconds=60,
        is_stale=True,
    )
    row = TaskRow(data)
    result = row.render()

    # Stale workers should have dim style applied to title
    assert len(result.spans) > 0, "Text should have style spans"
    title_span = result.spans[0]
    style_str = str(title_span.style).lower()
    # Should have dim style instead of bright green
    assert "dim" in style_str, f"Stale worker should have dim style, got: {title_span.style}"


# ===== Tests for Task #2905: Constants + TaskRow v2 =====


def test_phase_badges_contains_new_keys() -> None:
    """PHASE_BADGES has spawn, slow, c1, exec with (text, color) tuples."""
    from formaltask.apps.dashboard.widgets.task_row import PHASE_BADGES

    for key in ["spawn", "slow", "c1", "exec"]:
        assert key in PHASE_BADGES, f"Missing key: {key}"
        text, color = PHASE_BADGES[key]
        assert isinstance(text, str) and len(text) > 0
        assert isinstance(color, str) and color.startswith("#")


def test_task_row_data_new_fields_have_defaults() -> None:
    """TaskRowData accepts row_marker, is_new, spawn_dots with defaults."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRowData

    d = TaskRowData(
        task_id=1, title="x", status="running",
        phase="implementing", elapsed_seconds=0,
    )
    assert d.row_marker == " "
    assert d.is_new is False
    assert d.spawn_dots == ""


def test_task_row_data_new_fields_accept_values() -> None:
    """TaskRowData new fields accept non-default values."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRowData

    d = TaskRowData(
        task_id=1, title="x", status="running",
        phase="implementing", elapsed_seconds=0,
        row_marker="▶", is_new=True, spawn_dots="●●",
    )
    assert d.row_marker == "▶"
    assert d.is_new is True
    assert d.spawn_dots == "●●"


def test_render_layout_with_new_fields() -> None:
    """render() output: [marker][epic:5][#id][title...][BADGE][time][NEW]."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=42, title="Auth flow", status="running",
        phase="implementing", elapsed_seconds=300,
        epic_name="auth", row_marker="▶", is_new=True,
    )
    row = TaskRow(data)
    result = row.render()
    plain = result.plain

    # Marker should appear first
    assert plain[0] == "▶"
    # Epic column (5 chars) follows marker
    epic_section = plain[1:6]
    assert "auth" in epic_section
    # Task ID after epic
    assert "#42" in plain
    # Badge should appear
    assert "IMPL" in plain
    # Time should appear
    assert "5m" in plain
    # NEW tag should appear at end
    assert "NEW" in plain

    # Order: marker before epic before #id before IMPL before time before NEW
    marker_pos = plain.find("▶")
    id_pos = plain.find("#42")
    badge_pos = plain.find("IMPL")
    time_pos = plain.find("5m")
    new_pos = plain.find("NEW")
    assert marker_pos < id_pos < badge_pos < time_pos < new_pos


# --- B2: spawn_dots in badge area ---


def test_spawn_dots_render_in_badge() -> None:
    """When phase=='spawn' and spawn_dots is set, badge shows spawn_dots."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Spawning",
        status="running",
        phase="spawn",
        elapsed_seconds=5,
        spawn_dots="...",
    )
    row = TaskRow(data)
    result = row.render()
    plain = result.plain

    # Badge area should show "..." (the spawn_dots) instead of "SPAWN"
    assert "..." in plain
    assert "SPAWN" not in plain


def test_spawn_dots_empty_falls_back_to_phase_badge() -> None:
    """When phase=='spawn' but spawn_dots is empty, badge shows 'SPAWN'."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1,
        title="Spawning",
        status="running",
        phase="spawn",
        elapsed_seconds=5,
        spawn_dots="",
    )
    row = TaskRow(data)
    result = row.render()
    plain = result.plain

    assert "SPAWN" in plain


def test_state_to_row_data_passes_spawn_dots() -> None:
    """_state_to_row_data passes spawn_dots from state dict to TaskRowData."""
    from formaltask.apps.dashboard.widgets.task_list import TaskList

    tl = TaskList()
    state = {
        "health_state": "spawn",
        "tmux_session_exists": True,
        "title": "t",
        "spawn_dots": "●●",
    }
    row_data = tl._state_to_row_data(1, state)
    assert row_data.spawn_dots == "●●"


def test_render_layout_with_defaults() -> None:
    """render() with default fields: no marker visible, no NEW tag, blank epic."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=1, title="Test", status="idle",
        phase="done", elapsed_seconds=60,
    )
    row = TaskRow(data)
    result = row.render()
    plain = result.plain

    # Default marker is space
    assert plain[0] == " "
    # No NEW tag
    assert "NEW" not in plain
    # Task ID present
    assert "#1" in plain
    # Badge present
    assert "DONE" in plain
    # Time present
    assert "1m" in plain


# ===== Tests for Task #2922: Aesthetic polish =====


def test_cursor_char_on_selected() -> None:
    """Selected row shows ▸ cursor character when it has --selected class."""
    from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

    data = TaskRowData(
        task_id=42,
        title="Selected task",
        status="running",
        phase="implementing",
        elapsed_seconds=120,
    )
    row = TaskRow(data)

    # Without --selected class, marker should be space (default)
    result = row.render()
    assert result.plain[0] == " ", f"Unselected row should have space marker, got: '{result.plain[0]}'"

    # Add --selected class (simulating selection)
    row.add_class("--selected")

    result = row.render()
    assert result.plain[0] == "\u25b8", (
        f"Selected row should have ▸ cursor char, got: '{result.plain[0]}'"
    )


def test_exit_badge_red() -> None:
    """EXIT badge renders in bold red (#f38ba8), not dim grey."""
    from formaltask.apps.dashboard.widgets.task_row import PHASE_BADGES, TaskRow, TaskRowData

    # Check PHASE_BADGES constant
    text, color = PHASE_BADGES["exited"]
    assert text == "EXIT"
    assert color == "#f38ba8", f"EXIT badge color should be #f38ba8 (red), got: {color}"

    # Also verify it renders with the red color in the actual badge span
    data = TaskRowData(
        task_id=99,
        title="Crashed task",
        status="error",
        phase="exited",
        elapsed_seconds=600,
    )
    row = TaskRow(data)
    result = row.render()
    plain = result.plain

    assert "EXIT" in plain

    # Find the span that covers the EXIT badge text
    exit_pos = plain.find("EXIT")
    for span in result.spans:
        if span.start <= exit_pos < span.end:
            style_str = str(span.style).lower()
            assert "#f38ba8" in style_str, (
                f"EXIT badge span should use #f38ba8, got: {span.style}"
            )
            break
