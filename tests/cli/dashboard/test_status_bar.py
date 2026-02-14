"""Tests for StatusBar widget."""

import re
import time


def test_update_stores_counts() -> None:
    """StatusBar.update() accepts counts and stores them for rendering."""
    from formaltask.apps.dashboard.widgets.status_bar import StatusBar

    bar = StatusBar()
    bar.update(
        epic_count=2,
        done=5,
        running=3,
        exit_count=1,
        help_count=1,
        queued=4,
        change_count=10,
    )

    # Verify stored values via render output
    result = bar.render()
    plain = result.plain
    assert "2 epics" in plain
    assert "5/" in plain  # done count
    assert "3 run" in plain
    assert "1 EXIT" in plain
    assert "1 HELP" in plain
    assert "4 queued" in plain
    assert "\u219110" in plain  # up-arrow + change_count


def test_render_format() -> None:
    """render() produces text containing epic count, done fraction, running count, and clock."""
    from formaltask.apps.dashboard.widgets.status_bar import StatusBar

    bar = StatusBar()
    bar.update(
        epic_count=2,
        done=5,
        running=3,
        exit_count=0,
        help_count=0,
        queued=4,
        change_count=0,
    )

    result = bar.render()
    plain = result.plain

    # Epic count
    assert "2 epics" in plain
    # Done fraction: done/total
    assert "5/12 done" in plain  # total = 5+3+0+0+4 = 12
    # Running count
    assert "3 run" in plain
    # Clock format HH:MM:SS
    assert re.search(r"\d{2}:\d{2}:\d{2}", plain), f"No clock in: {plain}"
    # Zero counts should not show EXIT/HELP/change
    assert "EXIT" not in plain
    assert "HELP" not in plain
    assert "\u2191" not in plain


def test_stale_detection() -> None:
    """Stale indicator appears in render output when last update was >5s ago."""
    from formaltask.apps.dashboard.widgets.status_bar import StatusBar

    bar = StatusBar()
    bar.update(
        epic_count=1,
        done=0,
        running=1,
        exit_count=0,
        help_count=0,
        queued=0,
        change_count=0,
    )

    # Immediately after update — no stale indicator
    result = bar.render()
    assert "\u23f8" not in result.plain, "Should NOT be stale right after update"

    # Simulate 6 seconds passing by backdating _last_update_time
    bar._last_update_time = time.monotonic() - 6.0

    result = bar.render()
    assert "\u23f8" in result.plain, "Should show stale indicator after >5s"


# ===== Tests for Task #2922: Aesthetic polish =====


def test_status_bar_dot_separators() -> None:
    """Status bar uses ' · ' (middle dot) separators between sections."""
    from formaltask.apps.dashboard.widgets.status_bar import StatusBar

    bar = StatusBar()
    bar.update(
        epic_count=2,
        done=5,
        running=3,
        exit_count=0,
        help_count=0,
        queued=4,
        change_count=0,
    )

    result = bar.render()
    plain = result.plain

    # Should use middle dot separators
    assert " \u00b7 " in plain, f"Expected ' · ' separator in: {plain}"
    # Should NOT use double-space separators (old behavior)
    # Between content sections there should be dots, not just spaces
    # Count middle dots - should have at least 3 (between epics, done, run, queued)
    assert plain.count("\u00b7") >= 3, f"Expected >= 3 dot separators, got {plain.count(chr(0xb7))} in: {plain}"


def test_epic_count_hidden_when_one() -> None:
    """Epic count hidden when only 1 epic active."""
    from formaltask.apps.dashboard.widgets.status_bar import StatusBar

    bar = StatusBar()
    bar.update(
        epic_count=1,
        done=2,
        running=1,
        exit_count=0,
        help_count=0,
        queued=0,
        change_count=0,
    )

    result = bar.render()
    plain = result.plain

    # Should NOT show "1 epics" or any epic count
    assert "epic" not in plain.lower(), f"Epic count should be hidden when 1: {plain}"

    # When 0 epics, also hide
    bar.update(
        epic_count=0,
        done=0,
        running=0,
        exit_count=0,
        help_count=0,
        queued=0,
        change_count=0,
    )
    result = bar.render()
    assert "epic" not in result.plain.lower(), "Epic count should be hidden when 0"

    # When 2+ epics, show
    bar.update(
        epic_count=3,
        done=0,
        running=1,
        exit_count=0,
        help_count=0,
        queued=0,
        change_count=0,
    )
    result = bar.render()
    assert "3 epics" in result.plain, "Epic count should show when > 1"
