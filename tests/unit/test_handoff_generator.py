"""Tests for handoff generator hook.

Main entry point for PreCompact hook that generates handoffs via GPT 5.2.
Worktree-only activation via .session/name file.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from hooks.pre_compact.handoff_generator import HandoffResponse


@pytest.fixture
def make_handoff_response():
    """Factory for real HandoffResponse instances with overridable defaults."""
    def _make(**overrides):
        defaults = dict(
            summary="Test",
            decisions=[],
            completed=[],
            pending=[],
            context="",
            files_touched=[],
        )
        defaults.update(overrides)
        return HandoffResponse(**defaults)
    return _make


class TestGenerateHandoff:
    """Integration tests for handoff generation flow."""

    def test_no_session_file_returns_none(self, tmp_path):
        """No .session/name file means no handoff generated."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        # Create transcript without .session/name
        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
        ]
        transcript.write_text("\n".join(json.dumps(l) for l in lines))

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        handoff_dir = tmp_path / "handoffs"

        result = generate_handoff(ctx, handoff_dir=handoff_dir)

        assert result is None
        assert not (handoff_dir / "thread-index.json").exists()

    def test_worktree_session_generates_handoff(self, tmp_path, make_handoff_response):
        """With .session/name, generates handoff using full transcript."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        # Create .session/name file
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("test-thread")

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "Do some work"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done!"}]}},
        ]
        transcript.write_text("\n".join(json.dumps(l) for l in lines))

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        handoff_dir = tmp_path / "handoffs"

        response = make_handoff_response(
            summary="Work was done", decisions=["Decision 1"], completed=["Task 1"],
        )

        with patch("hooks.pre_compact.handoff_generator.get_openrouter_client") as mock_client:
            client = MagicMock()
            mock_client.return_value = (client, "openai/gpt-5.2")
            client.chat.completions.create.return_value = response

            result = generate_handoff(ctx, handoff_dir=handoff_dir)

        assert result is not None
        assert result.exists()
        assert result.parent.name == "test-thread"  # Thread name is directory
        assert result.name.startswith("01--")  # Sequence number format
        assert result.suffix == ".md"

        # Verify client called with correct model
        mock_client.assert_called_once_with(model="openai/gpt-5.2")

    def test_writes_stub_on_api_failure(self, tmp_path):
        """API failure writes stub handoff for recovery."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        # Create .session/name file
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("failing-thread")

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "Work here"}},
        ]
        transcript.write_text("\n".join(json.dumps(l) for l in lines))

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        handoff_dir = tmp_path / "handoffs"

        with patch("hooks.pre_compact.handoff_generator.get_openrouter_client") as mock_client:
            mock_client.side_effect = ValueError("API key not found")

            result = generate_handoff(ctx, handoff_dir=handoff_dir)

        assert result is not None
        assert result.exists()
        assert "STUB" in result.name
        text = result.read_text()
        assert "API key not found" in text
        assert str(transcript) in text

    def test_handles_openrouter_rate_limit(self, tmp_path):
        """Rate limit error writes stub."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        # Create .session/name file
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("rate-limited")

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "Work"}},
        ]
        transcript.write_text("\n".join(json.dumps(l) for l in lines))

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        handoff_dir = tmp_path / "handoffs"

        with patch("hooks.pre_compact.handoff_generator.get_openrouter_client") as mock_client:
            client = MagicMock()
            mock_client.return_value = (client, "openai/gpt-5.2")
            client.chat.completions.create.side_effect = Exception("429 Too Many Requests")

            result = generate_handoff(ctx, handoff_dir=handoff_dir)

        assert result is not None
        assert "STUB" in result.name

    def test_missing_transcript_path_returns_none(self, tmp_path):
        """No transcript_path in context returns None."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        ctx = {}
        result = generate_handoff(ctx, handoff_dir=tmp_path)

        assert result is None

    def test_nonexistent_transcript_returns_none(self, tmp_path):
        """Transcript path that doesn't exist returns None."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        ctx = {"transcript_path": "/nonexistent/path.jsonl"}
        result = generate_handoff(ctx, handoff_dir=tmp_path)

        assert result is None

    def test_uses_full_transcript_for_worktree_session(self, tmp_path, make_handoff_response):
        """Worktree sessions use the entire transcript (start_line=0)."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        # Create .session/name file
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("full-transcript-test")

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "First message"}},
            {"type": "user", "message": {"content": "Second message"}},
            {"type": "user", "message": {"content": "Third message"}},
        ]
        transcript.write_text("\n".join(json.dumps(l) for l in lines))

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        handoff_dir = tmp_path / "handoffs"

        captured_content = []
        response = make_handoff_response()

        with patch("hooks.pre_compact.handoff_generator.get_openrouter_client") as mock_client:
            client = MagicMock()
            mock_client.return_value = (client, "openai/gpt-5.2")

            def capture_call(**kwargs):
                msgs = kwargs.get("messages", [])
                for m in msgs:
                    if m.get("role") == "user":
                        captured_content.append(m.get("content", ""))
                return response

            client.chat.completions.create.side_effect = capture_call

            generate_handoff(ctx, handoff_dir=handoff_dir)

        # All three messages should be in the transcript sent to LLM
        assert len(captured_content) == 1
        transcript_sent = captured_content[0]
        assert "First message" in transcript_sent
        assert "Second message" in transcript_sent
        assert "Third message" in transcript_sent


class TestHandoffPrompt:
    """Test the system prompt sent to GPT 5.2."""

    def test_prompt_includes_context_instructions(self, tmp_path, make_handoff_response):
        """Prompt guides GPT to extract decision rationale and blockers."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        # Create .session/name file
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("prompt-test")

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "test content"}},
        ]
        transcript.write_text("\n".join(json.dumps(l) for l in lines))

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        handoff_dir = tmp_path / "handoffs"

        captured_messages = []
        response = make_handoff_response()

        with patch("hooks.pre_compact.handoff_generator.get_openrouter_client") as mock_client:
            client = MagicMock()
            mock_client.return_value = (client, "openai/gpt-5.2")

            def capture_call(**kwargs):
                captured_messages.extend(kwargs.get("messages", []))
                return response

            client.chat.completions.create.side_effect = capture_call

            generate_handoff(ctx, handoff_dir=handoff_dir)

        # Check system prompt content
        system_msg = next((m for m in captured_messages if m.get("role") == "system"), None)
        assert system_msg is not None
        content = system_msg["content"]
        assert "rationale" in content.lower() or "decision" in content.lower()
        assert "blocker" in content.lower() or "failed" in content.lower()


class TestHandoffResponseModel:
    """Test the Pydantic response model."""

    def test_model_validates_fields(self):
        """HandoffResponse validates all expected fields."""
        from hooks.pre_compact.handoff_generator import HandoffResponse

        response = HandoffResponse(
            summary="Test summary",
            decisions=["D1"],
            completed=["C1"],
            pending=["P1"],
            context="Some context",
            files_touched=["file.py"],
        )

        assert response.summary == "Test summary"
        assert response.decisions == ["D1"]
        assert len(response.files_touched) == 1

    def test_model_has_defaults(self):
        """Model fields have sensible defaults."""
        from hooks.pre_compact.handoff_generator import HandoffResponse

        response = HandoffResponse(summary="Just summary")

        assert response.decisions == []
        assert response.completed == []
        assert response.pending == []
        assert response.context == ""
        assert response.files_touched == []


class TestBreadcrumbWriting:
    """Test breadcrumb writing during handoff generation."""

    def test_writes_breadcrumb_when_project_id_present(self, tmp_path, make_handoff_response):
        """Writes thread breadcrumb when project_id is in context."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        # Create .session/name file
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("auth-refactor")

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "Work here"}},
        ]
        transcript.write_text("\n".join(json.dumps(line) for line in lines))

        handoff_dir = tmp_path / "handoffs"
        projects_dir = tmp_path / "projects"

        ctx = {
            "transcript_path": str(transcript),
            "cwd": str(tmp_path),
            "project_id": "test-project-123",
        }

        with patch("hooks.pre_compact.handoff_generator.get_openrouter_client") as mock_client:
            client = MagicMock()
            mock_client.return_value = (client, "openai/gpt-5.2")
            client.chat.completions.create.return_value = make_handoff_response()

            generate_handoff(ctx, handoff_dir=handoff_dir, projects_dir=projects_dir)

        # Verify breadcrumb was written
        breadcrumb = projects_dir / "test-project-123" / "handoff-thread.txt"
        assert breadcrumb.exists()
        assert breadcrumb.read_text() == "auth-refactor"

    def test_no_breadcrumb_without_project_id(self, tmp_path, make_handoff_response):
        """No breadcrumb written when project_id is missing."""
        from hooks.pre_compact.handoff_generator import generate_handoff

        # Create .session/name file
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("no-project")

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "Work here"}},
        ]
        transcript.write_text("\n".join(json.dumps(line) for line in lines))

        handoff_dir = tmp_path / "handoffs"
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}  # No project_id

        with patch("hooks.pre_compact.handoff_generator.get_openrouter_client") as mock_client:
            client = MagicMock()
            mock_client.return_value = (client, "openai/gpt-5.2")
            client.chat.completions.create.return_value = make_handoff_response()

            generate_handoff(ctx, handoff_dir=handoff_dir, projects_dir=projects_dir)

        # No breadcrumb should exist
        assert not list(projects_dir.glob("*/handoff-thread.txt"))
