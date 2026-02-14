"""Tests for subagent_step_tracker PreToolUse hook."""

import json
from unittest.mock import MagicMock, patch

import pytest

# Ensure _HAS_LIFE_DB is True for all tests so check() doesn't short-circuit
_LIFE_DB_PATCH = patch("hooks.pretool.phases.subagent_step_tracker._HAS_LIFE_DB", True)


@pytest.fixture(autouse=True)
def _enable_life_db():
    with _LIFE_DB_PATCH:
        yield


def _make_ctx(prompt: str, session_id: str | None = None) -> dict:
    ctx = {
        "tool_name": "Task",
        "tool_input": {"prompt": prompt, "subagent_type": "general-purpose"},
    }
    if session_id:
        ctx["session_id"] = session_id
    return ctx


class TestNonTaskToolIgnored:
    """Non-Task tool calls should be ignored."""

    def test_read_tool_ignored(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        result = check({"tool_name": "Read", "tool_input": {"file_path": "/foo"}})
        assert result is None

    def test_write_tool_ignored(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        result = check({"tool_name": "Write", "tool_input": {"file_path": "/foo"}})
        assert result is None


class TestNoStepReferences:
    """Task calls without step file references should be no-ops."""

    def test_prompt_without_step_refs(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx("Research the codebase for auth patterns")
        with patch("hooks.pretool.phases.subagent_step_tracker.get_db") as mock_get_db:
            result = check(ctx)
        assert result is None
        mock_get_db.assert_not_called()

    def test_empty_prompt(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = {"tool_name": "Task", "tool_input": {"prompt": ""}}
        result = check(ctx)
        assert result is None


class TestAppendsToActiveSpan:
    """Step references with active spans should append."""

    def test_single_step_appended(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx(
            "Read /Users/me/.claude/skills/review/steps/classify.md and execute",
            session_id="sess-1",
        )

        mock_db = MagicMock()
        mock_row = {"span_id": "span-abc", "steps": json.dumps(["SKILL", "bootstrap"])}
        mock_db.execute.return_value.fetchone.return_value = mock_row

        with (
            patch(
                "hooks.pretool.phases.subagent_step_tracker.get_db",
                return_value=mock_db,
            ),
            patch("hooks.pretool.phases.subagent_step_tracker.emit_event"),
        ):
            result = check(ctx)

        assert result is None  # never blocks

        # Verify UPDATE was called with appended step
        update_calls = [
            c for c in mock_db.execute.call_args_list if "UPDATE" in str(c)
        ]
        assert len(update_calls) == 1
        args = update_calls[0][0]
        assert args[1][0] == "classify"  # last_step
        assert json.loads(args[1][1]) == ["SKILL", "bootstrap", "classify"]

    def test_emits_life_event(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx(
            "Follow /skills/review/steps/feedback.md",
            session_id="sess-1",
        )

        mock_db = MagicMock()
        mock_row = {"span_id": "span-abc", "steps": json.dumps(["SKILL"])}
        mock_db.execute.return_value.fetchone.return_value = mock_row

        with (
            patch(
                "hooks.pretool.phases.subagent_step_tracker.get_db",
                return_value=mock_db,
            ),
            patch(
                "hooks.pretool.phases.subagent_step_tracker.emit_event"
            ) as mock_emit,
        ):
            check(ctx)

        mock_emit.assert_called_once_with(
            "review", "feedback", event_type="subagent_step_delegate"
        )


class TestNoActiveSpan:
    """When no active span exists, should be a no-op."""

    def test_no_active_span_skips(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx(
            "Read /skills/orphan-skill/steps/foo.md",
            session_id="sess-1",
        )

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None

        with (
            patch(
                "hooks.pretool.phases.subagent_step_tracker.get_db",
                return_value=mock_db,
            ),
            patch(
                "hooks.pretool.phases.subagent_step_tracker.emit_event"
            ) as mock_emit,
        ):
            result = check(ctx)

        assert result is None
        mock_emit.assert_not_called()
        update_calls = [
            c for c in mock_db.execute.call_args_list if "UPDATE" in str(c)
        ]
        assert len(update_calls) == 0


class TestInternalSkillIgnored:
    """Skills starting with _ should be ignored."""

    def test_internal_skill_skipped(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx("Read /skills/_partials/steps/foo.md")

        with patch(
            "hooks.pretool.phases.subagent_step_tracker.get_db"
        ) as mock_get_db:
            result = check(ctx)

        assert result is None
        mock_get_db.assert_not_called()


class TestSessionIsolation:
    """Span queries must be scoped by session_id."""

    def test_query_includes_session_id(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx(
            "Read /skills/my-skill/steps/step-a.md",
            session_id="sess-99",
        )

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None

        with (
            patch(
                "hooks.pretool.phases.subagent_step_tracker.get_db",
                return_value=mock_db,
            ),
            patch("hooks.pretool.phases.subagent_step_tracker.emit_event"),
        ):
            check(ctx)

        sql = mock_db.execute.call_args[0][0]
        params = mock_db.execute.call_args[0][1]
        assert "session_id = ?" in sql
        assert "sess-99" in params

    def test_no_session_id_still_works(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx("Read /skills/my-skill/steps/step-a.md")

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None

        with (
            patch(
                "hooks.pretool.phases.subagent_step_tracker.get_db",
                return_value=mock_db,
            ),
            patch("hooks.pretool.phases.subagent_step_tracker.emit_event"),
        ):
            check(ctx)

        sql = mock_db.execute.call_args[0][0]
        assert "session_id" not in sql


class TestFailOpen:
    """DB errors should not block tool calls."""

    def test_db_error_returns_none(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx(
            "Read /skills/my-skill/steps/step-a.md",
            session_id="sess-1",
        )

        with patch(
            "hooks.pretool.phases.subagent_step_tracker.get_db",
            side_effect=Exception("DB locked"),
        ):
            result = check(ctx)

        assert result is None


class TestDuplicateStepSkipped:
    """If the step is already the last step, don't append again."""

    def test_same_step_not_appended_twice(self):
        from hooks.pretool.phases.subagent_step_tracker import check

        ctx = _make_ctx(
            "Read /skills/my-skill/steps/classify.md",
            session_id="sess-1",
        )

        mock_db = MagicMock()
        mock_row = {
            "span_id": "span-abc",
            "steps": json.dumps(["SKILL", "classify"]),
        }
        mock_db.execute.return_value.fetchone.return_value = mock_row

        with (
            patch(
                "hooks.pretool.phases.subagent_step_tracker.get_db",
                return_value=mock_db,
            ),
            patch(
                "hooks.pretool.phases.subagent_step_tracker.emit_event"
            ) as mock_emit,
        ):
            result = check(ctx)

        assert result is None
        mock_emit.assert_not_called()
        update_calls = [
            c for c in mock_db.execute.call_args_list if "UPDATE" in str(c)
        ]
        assert len(update_calls) == 0
