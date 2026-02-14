"""Tests for SessionEnd vault_capture phase — summarizer-based flow."""

from unittest.mock import patch

import pytest


@pytest.fixture
def vault_dir(tmp_path):
    d = tmp_path / "vault"
    d.mkdir()
    return d


class TestVaultCapture:
    def test_skips_worker_sessions(self, tmp_path, monkeypatch):
        """Workers (.task/id present) should be skipped."""
        from hooks.session_end.phases.vault_capture import vault_capture

        task_dir = tmp_path / ".task"
        task_dir.mkdir()
        (task_dir / "id").write_text("42")
        monkeypatch.chdir(tmp_path)

        vault_capture({"session_id": "test-id"})

    def test_skips_without_api_key(self, tmp_path, monkeypatch):
        """Missing OPENROUTER_API_KEY should skip."""
        from hooks.session_end.phases.vault_capture import vault_capture

        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)

        vault_capture({"session_id": "test-id"})

    def test_skips_without_session_id(self):
        """No session_id means nothing to capture."""
        from hooks.session_end.phases.vault_capture import vault_capture

        vault_capture({})

    def test_updates_and_renames_existing_summary(self, tmp_path, monkeypatch, vault_dir):
        """Existing summary gets updated, then renamed to slug in sessions/{week}/."""
        from hooks.session_end.phases.vault_capture import vault_capture

        # Pre-existing summary in sessions subfolder
        week = vault_dir / "sessions" / "2026-W07"
        week.mkdir(parents=True)
        existing = week / "2026-02-09-abc12345.md"
        existing.write_text("---\nconcepts: [hooks]\n---\n# Auth Flow\nOriginal summary.")

        # pages dir for materialize
        (vault_dir / "pages").mkdir()

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        transcript = tmp_path / "abc12345678.jsonl"
        transcript.write_text('{"type":"user","message":{"content":"test"}}\n')

        with (
            patch("hooks.session_end.phases.vault_capture.VAULT_DIR", vault_dir),
            patch("hooks.session_end.phases.vault_capture._find_transcript", return_value=transcript),
            patch("hooks.session_end.phases.vault_capture.handoff_transcript", return_value="x" * 300),
            patch("hooks.session_end.phases.vault_capture.find_last_compaction_line", return_value=0),
            patch("hooks.session_end.phases.vault_capture.summarize_update", return_value="---\nconcepts: [hooks]\n---\n# Auth Flow\nUpdated summary."),
            patch("hooks.session_end.phases.vault_capture.find_summary", return_value=existing),
            patch("hooks.session_end.phases.vault_capture.get_concept_list", return_value=["hooks"]),
            patch("hooks.session_end.phases.vault_capture.update_concept_cache"),
            patch("hooks.session_end.phases.vault_capture.materialize_concepts") as mock_materialize,
            patch("hooks.session_end.phases.vault_capture.generate_session_index") as mock_index,
        ):
            vault_capture({"session_id": "abc12345678"})

        # Original file should be renamed to slug-based name
        assert not existing.exists()
        slugged = list(week.glob("*auth-flow-abc1*.md"))
        assert len(slugged) == 1
        assert "Updated summary" in slugged[0].read_text()
        mock_materialize.assert_called_once()
        mock_index.assert_called_once()

    def test_creates_summary_for_new_session(self, tmp_path, monkeypatch, vault_dir):
        """Session without prior summary creates one in sessions/{week}/."""
        from hooks.session_end.phases.vault_capture import vault_capture

        transcript = tmp_path / "abc12345678.jsonl"
        lines = ['{"type":"user","message":{"content":"msg"}}\n'] * 6
        transcript.write_text("".join(lines))

        (vault_dir / "pages").mkdir()

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        with (
            patch("hooks.session_end.phases.vault_capture.VAULT_DIR", vault_dir),
            patch("hooks.session_end.phases.vault_capture._find_transcript", return_value=transcript),
            patch("hooks.session_end.phases.vault_capture.handoff_transcript", return_value="x" * 300),
            patch("hooks.session_end.phases.vault_capture.find_last_compaction_line", return_value=0),
            patch("hooks.session_end.phases.vault_capture.count_user_turns", return_value=6),
            patch("hooks.session_end.phases.vault_capture.summarize_base", return_value="---\nconcepts: [hooks]\n---\n# New Topic\nFresh summary."),
            patch("hooks.session_end.phases.vault_capture.find_summary", return_value=None),
            patch("hooks.session_end.phases.vault_capture.get_concept_list", return_value=[]),
            patch("hooks.session_end.phases.vault_capture.update_concept_cache"),
            patch("hooks.session_end.phases.vault_capture.materialize_concepts"),
            patch("hooks.session_end.phases.vault_capture.generate_session_index") as mock_index,
        ):
            vault_capture({"session_id": "abc12345678"})

        # File should be in sessions/ with slug name
        sessions_dir = vault_dir / "sessions"
        assert sessions_dir.is_dir()
        all_md = list(sessions_dir.rglob("*.md"))
        assert len(all_md) == 1
        assert "new-topic" in all_md[0].name
        assert "Fresh summary" in all_md[0].read_text()
        mock_index.assert_called_once()

    def test_skips_trivial_session(self, tmp_path, monkeypatch, vault_dir):
        """Sessions below MIN_TURNS without prior summary are skipped."""
        from hooks.session_end.phases.vault_capture import vault_capture

        transcript = tmp_path / "abc12345678.jsonl"
        transcript.write_text('{"type":"user","message":{"content":"hi"}}\n')

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        with (
            patch("hooks.session_end.phases.vault_capture.VAULT_DIR", vault_dir),
            patch("hooks.session_end.phases.vault_capture._find_transcript", return_value=transcript),
            patch("hooks.session_end.phases.vault_capture.handoff_transcript", return_value="x" * 300),
            patch("hooks.session_end.phases.vault_capture.find_last_compaction_line", return_value=0),
            patch("hooks.session_end.phases.vault_capture.count_user_turns", return_value=2),
            patch("hooks.session_end.phases.vault_capture.find_summary", return_value=None),
            patch("hooks.session_end.phases.vault_capture.get_concept_list", return_value=[]),
        ):
            vault_capture({"session_id": "abc12345678"})

        sessions_dir = vault_dir / "sessions"
        if sessions_dir.exists():
            assert list(sessions_dir.rglob("*.md")) == []

    def test_fail_open(self, tmp_path, monkeypatch):
        """Exceptions should not propagate."""
        from hooks.session_end.phases.vault_capture import vault_capture

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.chdir(tmp_path)

        with patch("hooks.session_end.phases.vault_capture._find_transcript", side_effect=RuntimeError("boom")):
            vault_capture({"session_id": "abc"})
