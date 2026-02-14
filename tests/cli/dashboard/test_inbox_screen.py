"""Tests for InboxScreen modal."""

from unittest.mock import MagicMock

from formaltask.apps.dashboard.screens.inbox import InboxScreen, _format_age


class TestFormatAge:
    def test_none(self):
        assert _format_age(None) == ""

    def test_seconds(self):
        assert _format_age(45) == "45s ago"

    def test_minutes(self):
        assert _format_age(180) == "3m ago"

    def test_hours(self):
        assert _format_age(7200) == "2h ago"


class TestInboxScreenInit:
    def test_creates_with_workers(self):
        workers = [
            {"task_id": 42, "task_title": "Fix bug", "pending_question": "Which approach?", "age_seconds": 120},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        assert len(screen.blocked_workers) == 1
        assert screen.selected_index == 0
        assert screen._replying is False

    def test_creates_with_empty_workers(self):
        screen = InboxScreen([], "/tmp/test.db")
        assert len(screen.blocked_workers) == 0

    def test_does_not_mutate_input_list(self):
        workers = [{"task_id": 1, "task_title": "T", "pending_question": "Q", "age_seconds": 0}]
        original = list(workers)
        InboxScreen(workers, "/tmp/test.db")
        assert workers == original


class TestInboxScreenNavigation:
    def test_next_clamps_to_end(self):
        workers = [
            {"task_id": 1, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
            {"task_id": 2, "task_title": "B", "pending_question": "Q2", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen.selected_index = 1
        # Can't go past end — _nav_next clamps
        screen._nav_next()
        assert screen.selected_index == 1

    def test_prev_clamps_to_start(self):
        workers = [
            {"task_id": 1, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen.selected_index = 0
        screen._nav_prev()
        assert screen.selected_index == 0

    def test_nav_blocked_during_reply(self):
        """on_key returns early when _replying — keys don't reach handlers."""
        workers = [
            {"task_id": 1, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
            {"task_id": 2, "task_title": "B", "pending_question": "Q2", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen._replying = True
        event = MagicMock()
        event.key = "j"
        screen.on_key(event)
        assert screen.selected_index == 0  # Didn't move


class TestInboxScreenDismiss:
    def test_dismiss_removes_worker_from_list(self):
        workers = [
            {"task_id": 1, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
            {"task_id": 2, "task_title": "B", "pending_question": "Q2", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen.selected_index = 0

        # Mock DOM operations (no running app)
        screen._clear_blocked_in_db = MagicMock()
        screen._refresh_inbox_list = MagicMock()

        screen._dismiss_blocked()

        assert len(screen.blocked_workers) == 1
        assert screen.blocked_workers[0]["task_id"] == 2
        screen._clear_blocked_in_db.assert_called_once_with(1)
        screen._refresh_inbox_list.assert_called_once()

    def test_dismiss_last_worker_dismisses_screen(self):
        workers = [
            {"task_id": 42, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen._clear_blocked_in_db = MagicMock()
        screen.dismiss = MagicMock()

        screen._dismiss_blocked()

        assert len(screen.blocked_workers) == 0
        screen._clear_blocked_in_db.assert_called_once_with(42)
        screen.dismiss.assert_called_once_with(None)

    def test_dismiss_blocked_during_reply_is_noop(self):
        workers = [
            {"task_id": 1, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen._replying = True
        screen._clear_blocked_in_db = MagicMock()

        screen._dismiss_blocked()

        assert len(screen.blocked_workers) == 1  # Not removed
        screen._clear_blocked_in_db.assert_not_called()

    def test_dismiss_empty_inbox_is_noop(self):
        screen = InboxScreen([], "/tmp/test.db")
        screen._clear_blocked_in_db = MagicMock()

        screen._dismiss_blocked()

        screen._clear_blocked_in_db.assert_not_called()


class TestInboxScreenSubmit:
    def test_submit_removes_worker_on_send(self):
        workers = [
            {"task_id": 42, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen._replying = True
        screen._send_response = MagicMock()
        screen.dismiss = MagicMock()

        # Simulate Input widget with value
        mock_input = MagicMock()
        mock_input.value = "  go ahead  "
        screen.query_one = MagicMock(return_value=mock_input)

        screen._submit_reply()

        screen._send_response.assert_called_once_with(42, "go ahead")
        screen.dismiss.assert_called_once_with(None)
        assert len(screen.blocked_workers) == 0

    def test_submit_empty_is_noop(self):
        workers = [
            {"task_id": 42, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen._send_response = MagicMock()

        mock_input = MagicMock()
        mock_input.value = "   "
        screen.query_one = MagicMock(return_value=mock_input)

        screen._submit_reply()

        screen._send_response.assert_not_called()

    def test_submit_guard_prevents_double_send(self):
        workers = [
            {"task_id": 42, "task_title": "A", "pending_question": "Q1", "age_seconds": 0},
        ]
        screen = InboxScreen(workers, "/tmp/test.db")
        screen._sending = True
        screen._send_response = MagicMock()

        screen._submit_reply()

        screen._send_response.assert_not_called()
