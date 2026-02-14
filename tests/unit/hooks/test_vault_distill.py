"""Tests for PreCompact vault_distill hook — summarizer-based flow."""

import io
import json
from unittest.mock import patch

import pytest


@pytest.fixture
def vault_dir(tmp_path):
    d = tmp_path / "vault"
    d.mkdir()
    return d


class TestVaultDistill:
    def test_skips_worker_sessions(self, tmp_path, monkeypatch):
        """Workers (.task/id present) should be skipped."""
        from hooks.pre_compact.vault_distill import vault_distill

        task_dir = tmp_path / ".task"
        task_dir.mkdir()
        (task_dir / "id").write_text("42")
        monkeypatch.chdir(tmp_path)

        vault_distill({"transcript_path": "/fake/path.jsonl"})

    def test_skips_without_api_key(self, tmp_path, monkeypatch):
        """Missing OPENROUTER_API_KEY should skip."""
        from hooks.pre_compact.vault_distill import vault_distill

        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)

        vault_distill({"transcript_path": "/fake/path.jsonl"})

    def test_skips_missing_transcript(self, tmp_path, monkeypatch):
        """Non-existent transcript should skip."""
        from hooks.pre_compact.vault_distill import vault_distill

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        vault_distill({"transcript_path": str(tmp_path / "missing.jsonl")})

    def test_creates_summary_in_week_folder(self, tmp_path, monkeypatch, vault_dir):
        """First compaction creates summary in sessions/{week}/ folder."""
        from hooks.pre_compact.vault_distill import vault_distill

        transcript = tmp_path / "abc12345.jsonl"
        lines = [json.dumps({"type": "user", "message": {"content": f"msg {i}"}}) for i in range(6)]
        transcript.write_text("\n".join(lines) + "\n")

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        with (
            patch("hooks.pre_compact.vault_distill.VAULT_DIR", vault_dir),
            patch("hooks.pre_compact.vault_distill.handoff_transcript", return_value="x" * 300),
            patch("hooks.pre_compact.vault_distill.find_last_compaction_line", return_value=0),
            patch("hooks.pre_compact.vault_distill.summarize_base", return_value="---\nconcepts: [hooks]\n---\n# Auth Flow\nWe built auth."),
            patch("hooks.pre_compact.vault_distill.count_user_turns", return_value=6),
            patch("hooks.pre_compact.vault_distill.get_concept_list", return_value=["hooks"]),
            patch("hooks.pre_compact.vault_distill.update_concept_cache") as mock_cache,
        ):
            vault_distill({"transcript_path": str(transcript)})

        # File should be in sessions/{week}/ not vault root
        sessions_dir = vault_dir / "sessions"
        assert sessions_dir.is_dir()
        week_dirs = list(sessions_dir.iterdir())
        assert len(week_dirs) == 1
        summaries = list(week_dirs[0].glob("*.md"))
        assert len(summaries) == 1
        assert "abc12345" in summaries[0].name
        assert "Auth Flow" in summaries[0].read_text()
        mock_cache.assert_called_once()

    def test_updates_existing_summary(self, tmp_path, monkeypatch, vault_dir):
        """Subsequent compaction updates the existing summary file."""
        from hooks.pre_compact.vault_distill import vault_distill

        transcript = tmp_path / "abc12345.jsonl"
        transcript.write_text('{"type":"user","message":{"content":"test"}}\n')

        # Pre-existing summary in sessions subfolder
        week = vault_dir / "sessions" / "2026-W07"
        week.mkdir(parents=True)
        existing = week / "2026-02-09-abc12345.md"
        existing.write_text("---\nconcepts: [hooks]\n---\n# Old Summary\nOriginal content.")

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        with (
            patch("hooks.pre_compact.vault_distill.VAULT_DIR", vault_dir),
            patch("hooks.pre_compact.vault_distill.handoff_transcript", return_value="x" * 300),
            patch("hooks.pre_compact.vault_distill.find_last_compaction_line", return_value=0),
            patch("hooks.pre_compact.vault_distill.summarize_update", return_value="---\nconcepts: [hooks]\n---\n# Updated Summary\nNew content."),
            patch("hooks.pre_compact.vault_distill.get_concept_list", return_value=["hooks"]),
            patch("hooks.pre_compact.vault_distill.update_concept_cache") as mock_cache,
        ):
            vault_distill({"transcript_path": str(transcript)})

        assert "Updated Summary" in existing.read_text()
        mock_cache.assert_called_once()

    def test_skips_below_turn_threshold(self, tmp_path, monkeypatch, vault_dir):
        """Sessions below MIN_TURNS should not get a summary."""
        from hooks.pre_compact.vault_distill import vault_distill

        transcript = tmp_path / "short.jsonl"
        transcript.write_text('{"type":"user","message":{"content":"hi"}}\n')

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        with (
            patch("hooks.pre_compact.vault_distill.VAULT_DIR", vault_dir),
            patch("hooks.pre_compact.vault_distill.handoff_transcript", return_value="x" * 300),
            patch("hooks.pre_compact.vault_distill.find_last_compaction_line", return_value=0),
            patch("hooks.pre_compact.vault_distill.count_user_turns", return_value=2),
            patch("hooks.pre_compact.vault_distill.get_concept_list", return_value=[]),
        ):
            vault_distill({"transcript_path": str(transcript)})

        sessions_dir = vault_dir / "sessions"
        if sessions_dir.exists():
            assert list(sessions_dir.rglob("*.md")) == []

    def test_fail_open_on_exception(self, tmp_path, monkeypatch):
        """Exceptions in vault_distill should be caught by main()."""
        from hooks.pre_compact.vault_distill import main

        transcript = tmp_path / "test.jsonl"
        transcript.write_text('{"type":"user","message":{"content":"test"}}\n')

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        payload = {"transcript_path": str(transcript)}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))

        with (
            patch("hooks.pre_compact.vault_distill.handoff_transcript", side_effect=RuntimeError("boom")),
            patch("hooks.pre_compact.vault_distill.find_last_compaction_line", return_value=0),
        ):
            main()
