"""Tests for PreCompact transcript_snapshot hook.

Saves raw transcript before compaction destroys it. Pure I/O, no LLM.
Activation: .session/name file in cwd (worktree-only).
"""

import json
from pathlib import Path


class TestFindLastCompactionLine:
    """Find the line number after the last compaction summary."""

    def test_returns_zero_when_no_compaction(self, tmp_path):
        """No compaction entry → start from line 0."""
        from hooks.pre_compact.transcript_snapshot import find_last_compaction_line

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))

        result = find_last_compaction_line(transcript)

        assert result == 0

    def test_finds_compaction_line(self, tmp_path):
        """Returns line after compaction entry."""
        from hooks.pre_compact.transcript_snapshot import find_last_compaction_line

        preamble = "This session is being continued from a previous conversation"
        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "old message"}},
            {"type": "user", "message": {"content": f"{preamble} summary here"}},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "new content"}]},
            },
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))

        result = find_last_compaction_line(transcript)

        assert result == 2  # Line after the compaction entry (0-indexed)

    def test_uses_last_compaction_when_multiple(self, tmp_path):
        """Multiple compaction entries → uses last one."""
        from hooks.pre_compact.transcript_snapshot import find_last_compaction_line

        preamble = "This session is being continued from a previous conversation"
        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "old message"}},
            {"type": "user", "message": {"content": f"{preamble} first summary"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "middle"}]}},
            {"type": "user", "message": {"content": f"{preamble} second summary"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "latest"}]}},
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))

        result = find_last_compaction_line(transcript)

        assert result == 4  # Line after the LAST compaction entry

    def test_handles_json_decode_errors(self, tmp_path):
        """Gracefully skips malformed JSON lines."""
        from hooks.pre_compact.transcript_snapshot import find_last_compaction_line

        preamble = "This session is being continued from a previous conversation"
        transcript = tmp_path / "session.jsonl"
        content = (
            "not valid json\n"
            '{"type": "user", "message": {"content": "' + preamble + ' summary"}}\n'
            '{"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}'
        )
        transcript.write_text(content)

        result = find_last_compaction_line(transcript)

        assert result == 2  # Skipped bad line, found compaction at line 1

    def test_ignores_assistant_entries_with_preamble(self, tmp_path):
        """Only user entries count as compaction markers."""
        from hooks.pre_compact.transcript_snapshot import find_last_compaction_line

        preamble = "This session is being continued from a previous conversation"
        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "hello"}},
            {"type": "assistant", "message": {"content": f"{preamble} in assistant"}},
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))

        result = find_last_compaction_line(transcript)

        assert result == 0  # Assistant entry doesn't count


class TestSnapshotTranscript:
    """PreCompact hook: snapshot transcript for post-compaction delta."""

    def _make_transcript(self, tmp_path: Path) -> Path:
        """Create a minimal JSONL transcript file."""
        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "implement the feature"}},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Sure, let me do that."}]},
            },
            {"type": "user", "message": {"content": "looks good, ship it"}},
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))
        return transcript

    def test_no_session_name_returns_none(self, tmp_path):
        """No .session/name → no snapshot (fast-exit)."""
        from hooks.pre_compact.transcript_snapshot import snapshot_transcript

        transcript = self._make_transcript(tmp_path)
        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}

        result = snapshot_transcript(ctx)

        assert result is None
        assert not (tmp_path / ".session" / "transcript_snapshot.json").exists()

    def test_creates_snapshot_with_session_name(self, tmp_path):
        """With .session/name → writes transcript_snapshot.json."""
        from hooks.pre_compact.transcript_snapshot import snapshot_transcript

        transcript = self._make_transcript(tmp_path)
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("my-thread-name")

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        result = snapshot_transcript(ctx)

        assert result is not None
        snapshot_path = session_dir / "transcript_snapshot.json"
        assert snapshot_path.exists()
        assert result == snapshot_path

    def test_snapshot_json_structure(self, tmp_path):
        """Snapshot contains thread_name, transcript, transcript_path, timestamp."""
        from hooks.pre_compact.transcript_snapshot import snapshot_transcript

        transcript = self._make_transcript(tmp_path)
        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("auth-refactor")

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        snapshot_transcript(ctx)

        snapshot = json.loads((session_dir / "transcript_snapshot.json").read_text())
        assert snapshot["thread_name"] == "auth-refactor"
        assert "implement the feature" in snapshot["transcript"]
        assert snapshot["transcript_path"] == str(transcript)
        assert "timestamp" in snapshot

    def test_transcript_excludes_tool_use(self, tmp_path):
        """Snapshot transcript strips tool_use and tool_result entries."""
        from hooks.pre_compact.transcript_snapshot import snapshot_transcript

        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "read the file"}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Let me read it."},
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "/secret"}},
                    ]
                },
            },
            {"type": "tool_result", "content": "secret file contents"},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}},
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))

        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("test-thread")

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        snapshot_transcript(ctx)

        snapshot = json.loads((session_dir / "transcript_snapshot.json").read_text())
        assert "/secret" not in snapshot["transcript"]
        assert "secret file contents" not in snapshot["transcript"]
        assert "Let me read it." in snapshot["transcript"]

    def test_no_transcript_path_returns_none(self, tmp_path):
        """Missing transcript_path in ctx → None."""
        from hooks.pre_compact.transcript_snapshot import snapshot_transcript

        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("test-thread")

        ctx = {"cwd": str(tmp_path)}
        result = snapshot_transcript(ctx)

        assert result is None

    def test_nonexistent_transcript_returns_none(self, tmp_path):
        """Transcript path that doesn't exist → None."""
        from hooks.pre_compact.transcript_snapshot import snapshot_transcript

        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("test-thread")

        ctx = {"transcript_path": str(tmp_path / "nonexistent.jsonl"), "cwd": str(tmp_path)}
        result = snapshot_transcript(ctx)

        assert result is None

    def test_extracts_from_last_compaction_not_full_transcript(self, tmp_path):
        """Snapshot only includes content AFTER last compaction."""
        from hooks.pre_compact.transcript_snapshot import snapshot_transcript

        preamble = "This session is being continued from a previous conversation"
        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"content": "old message before compaction"}},
            {"type": "user", "message": {"content": f"{preamble} summary here"}},
            {"type": "user", "message": {"content": "new message after compaction"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "response"}]}},
        ]
        transcript.write_text("\n".join(json.dumps(e) for e in lines))

        session_dir = tmp_path / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("test-thread")

        ctx = {"transcript_path": str(transcript), "cwd": str(tmp_path)}
        snapshot_transcript(ctx)

        snapshot = json.loads((session_dir / "transcript_snapshot.json").read_text())
        assert "old message before compaction" not in snapshot["transcript"]
        assert "new message after compaction" in snapshot["transcript"]
