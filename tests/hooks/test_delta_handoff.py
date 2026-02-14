"""Tests for SessionStart delta_handoff hook.

Generates delta handoff from compaction gap: what Claude's summary missed.
Activation: .session/transcript_snapshot.json exists (written by PreCompact).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hooks.session_start.delta_handoff import DeltaHandoff


@pytest.fixture
def make_delta_response():
    """Factory for real DeltaHandoff instances with overridable defaults."""
    def _make(**overrides):
        defaults = dict(
            decision_rationale=[],
            failed_approaches=[],
            user_corrections=[],
            technical_gotchas=[],
            implementation_proposals=[],
        )
        defaults.update(overrides)
        return DeltaHandoff(**defaults)
    return _make


# -- generate_delta -------------------------------------------------------


class TestGenerateDelta:
    """SessionStart hook: generate delta handoff from compaction gap."""

    def _setup_snapshot(self, tmp_path: Path, thread_name: str = "test-thread") -> Path:
        """Create .session/transcript_snapshot.json and a JSONL transcript."""
        session_dir = tmp_path / ".session"
        session_dir.mkdir(exist_ok=True)

        transcript = tmp_path / "session.jsonl"
        preamble = "This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.\n\n"
        footer = "\n\nPlease continue the conversation from where we left it off without repeating anything."
        lines = [
            {"type": "user", "message": {"content": "implement auth"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Sure."}]}},
            {"type": "user", "message": {"content": preamble + "We added auth." + footer}},
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))

        snapshot = {
            "thread_name": thread_name,
            "transcript": "USER: implement auth\nCLAUDE: Sure.\n",
            "transcript_path": str(transcript),
            "timestamp": "2026-02-03T12:30:00Z",
        }
        snapshot_path = session_dir / "transcript_snapshot.json"
        snapshot_path.write_text(json.dumps(snapshot))
        return snapshot_path

    def test_fast_exit_without_snapshot(self, tmp_path):
        """No snapshot marker → returns None immediately."""
        from hooks.session_start.delta_handoff import generate_delta

        ctx = {"cwd": str(tmp_path)}
        result = generate_delta(ctx)

        assert result is None

    @patch("hooks.session_start.delta_handoff.get_openrouter_client")
    @patch("hooks.session_start.delta_handoff.write_handoff")
    def test_calls_llm_with_transcript(self, mock_write, mock_client, tmp_path, make_delta_response):
        """LLM receives the transcript for context extraction."""
        from hooks.session_start.delta_handoff import generate_delta

        self._setup_snapshot(tmp_path)

        mock_instructor = MagicMock()
        mock_client.return_value = (mock_instructor, "openai/gpt-5.2")

        mock_instructor.chat.completions.create.return_value = make_delta_response(
            decision_rationale=["Chose JWT over sessions"],
            failed_approaches=["Tried cookie auth first"],
            user_corrections=["User wanted stateless auth"],
            technical_gotchas=["Token refresh needs /api/refresh endpoint"],
            implementation_proposals=["Auth uses RS256 keys in /api/auth"],
        )

        mock_write.return_value = tmp_path / "handoff.md"

        ctx = {"cwd": str(tmp_path)}
        generate_delta(ctx)

        # Verify LLM was called with transcript
        call_args = mock_instructor.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_msg = messages[-1]["content"]
        assert "implement auth" in user_msg  # transcript content present

    @patch("hooks.session_start.delta_handoff.get_openrouter_client")
    @patch("hooks.session_start.delta_handoff.write_handoff")
    def test_passes_xhigh_reasoning_effort(self, mock_write, mock_client, tmp_path, make_delta_response):
        """LLM call includes extra_body with reasoning effort xhigh."""
        from hooks.session_start.delta_handoff import generate_delta

        self._setup_snapshot(tmp_path)

        mock_instructor = MagicMock()
        mock_client.return_value = (mock_instructor, "openai/gpt-5.2")

        mock_instructor.chat.completions.create.return_value = make_delta_response()

        mock_write.return_value = tmp_path / "handoff.md"

        ctx = {"cwd": str(tmp_path)}
        generate_delta(ctx)

        call_args = mock_instructor.chat.completions.create.call_args
        assert call_args.kwargs["extra_body"] == {"reasoning": {"effort": "xhigh"}}

    @patch("hooks.session_start.delta_handoff.get_openrouter_client")
    @patch("hooks.session_start.delta_handoff.write_handoff")
    def test_writes_handoff_with_delta_content(self, mock_write, mock_client, tmp_path, make_delta_response):
        """Delta content is written via write_handoff."""
        from hooks.session_start.delta_handoff import generate_delta

        self._setup_snapshot(tmp_path)

        mock_instructor = MagicMock()
        mock_client.return_value = (mock_instructor, "openai/gpt-5.2")

        mock_instructor.chat.completions.create.return_value = make_delta_response(
            decision_rationale=["Chose JWT"],
            failed_approaches=["Cookie auth"],
            technical_gotchas=["Refresh endpoint"],
            implementation_proposals=["RS256 keys"],
        )

        mock_write.return_value = tmp_path / "handoff.md"

        ctx = {"cwd": str(tmp_path)}
        generate_delta(ctx)

        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert call_args.args[0] == "test-thread"  # thread_name
        content = call_args.args[1]
        assert "Chose JWT" in content["summary"]

    @patch("hooks.session_start.delta_handoff.get_openrouter_client")
    @patch("hooks.session_start.delta_handoff.write_handoff")
    def test_deletes_snapshot_after_consumption(self, mock_write, mock_client, tmp_path, make_delta_response):
        """Snapshot file is deleted after successful delta generation."""
        from hooks.session_start.delta_handoff import generate_delta

        snapshot_path = self._setup_snapshot(tmp_path)
        assert snapshot_path.exists()

        mock_instructor = MagicMock()
        mock_client.return_value = (mock_instructor, "openai/gpt-5.2")

        mock_instructor.chat.completions.create.return_value = make_delta_response()

        mock_write.return_value = tmp_path / "handoff.md"

        ctx = {"cwd": str(tmp_path)}
        generate_delta(ctx)

        assert not snapshot_path.exists()

    @patch("hooks.session_start.delta_handoff.get_openrouter_client")
    @patch("hooks.session_start.delta_handoff.write_handoff")
    def test_returns_hook_output_dict(self, mock_write, mock_client, tmp_path, make_delta_response):
        """Returns hookSpecificOutput with additionalContext."""
        from hooks.session_start.delta_handoff import generate_delta

        self._setup_snapshot(tmp_path)

        mock_instructor = MagicMock()
        mock_client.return_value = (mock_instructor, "openai/gpt-5.2")

        mock_instructor.chat.completions.create.return_value = make_delta_response(
            decision_rationale=["Chose JWT"],
            technical_gotchas=["Refresh endpoint"],
            implementation_proposals=["RS256 keys in /api/auth"],
        )

        mock_write.return_value = tmp_path / "handoff.md"

        ctx = {"cwd": str(tmp_path)}
        result = generate_delta(ctx)

        assert result is not None
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        additional = result["hookSpecificOutput"]["additionalContext"]
        assert "Chose JWT" in additional
        assert "RS256 keys" in additional
        assert "Refresh endpoint" in additional

    @patch("hooks.session_start.delta_handoff.get_openrouter_client")
    @patch("hooks.session_start.delta_handoff.write_handoff")
    @patch("hooks.session_start.delta_handoff.write_thread_breadcrumb")
    def test_writes_breadcrumb_with_project_id(
        self, mock_breadcrumb, mock_write, mock_client, tmp_path, make_delta_response
    ):
        """Breadcrumb written when project_id present in ctx."""
        from hooks.session_start.delta_handoff import generate_delta

        self._setup_snapshot(tmp_path)

        mock_instructor = MagicMock()
        mock_client.return_value = (mock_instructor, "openai/gpt-5.2")

        mock_instructor.chat.completions.create.return_value = make_delta_response()

        mock_write.return_value = tmp_path / "handoff.md"

        ctx = {"cwd": str(tmp_path), "project_id": "proj-123"}
        generate_delta(ctx)

        mock_breadcrumb.assert_called_once_with("test-thread", "proj-123")

    @patch("hooks.session_start.delta_handoff.get_openrouter_client")
    @patch("hooks.session_start.delta_handoff.write_handoff")
    def test_fallback_when_no_compaction_summary(self, mock_write, mock_client, tmp_path, make_delta_response):
        """No compaction summary in JSONL → still generates from transcript alone."""
        from hooks.session_start.delta_handoff import generate_delta

        session_dir = tmp_path / ".session"
        session_dir.mkdir()

        # Transcript WITHOUT compaction summary
        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "do the thing"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}},
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))

        snapshot = {
            "thread_name": "test-thread",
            "transcript": "USER: do the thing\nCLAUDE: Done.\n",
            "transcript_path": str(transcript),
            "timestamp": "2026-02-03T12:30:00Z",
        }
        (session_dir / "transcript_snapshot.json").write_text(json.dumps(snapshot))

        mock_instructor = MagicMock()
        mock_client.return_value = (mock_instructor, "openai/gpt-5.2")

        mock_instructor.chat.completions.create.return_value = make_delta_response(
            implementation_proposals=["context from full transcript"],
        )

        mock_write.return_value = tmp_path / "handoff.md"

        ctx = {"cwd": str(tmp_path)}
        result = generate_delta(ctx)

        # Should still call LLM with transcript (no summary)
        assert result is not None
        call_args = mock_instructor.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_msg = messages[-1]["content"]
        assert "do the thing" in user_msg
