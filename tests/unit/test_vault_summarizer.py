"""Tests for vault summarizer — incremental session summaries."""

import json
from unittest.mock import MagicMock, patch

import openai
import pytest

from formaltask.vault.summarizer import (
    count_user_turns,
    extract_title,
    find_summary,
    slugify_title,
    summarize_base,
    summarize_update,
    validate_frontmatter,
)


@pytest.fixture
def vault_dir(tmp_path):
    return tmp_path / "vault"


@pytest.fixture
def transcript(tmp_path):
    """Create a JSONL transcript with user/assistant turns."""
    path = tmp_path / "abc12345.jsonl"
    entries = [
        {"type": "user", "message": {"content": "Hello"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}},
        {"type": "user", "message": {"content": "Build a thing"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done"}]}},
        {"type": "user", "message": {"content": "Fix the bug"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Fixed"}]}},
        {"type": "user", "message": {"content": "Add tests"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Added"}]}},
        {"type": "user", "message": {"content": "Ship it"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Shipped"}]}},
        {"type": "user", "message": {"content": "One more thing"}},
    ]
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return path


class TestSlugifyTitle:
    def test_basic(self):
        assert slugify_title("# Vault Architecture Redesign") == "vault-architecture-redesign"

    def test_strips_hash(self):
        assert slugify_title("## Key Decisions") == "key-decisions"

    def test_special_chars(self):
        assert slugify_title("# Email Triage (v2)") == "email-triage-v2"

    def test_truncates_long_titles(self):
        long = "# " + "a" * 100
        result = slugify_title(long)
        assert len(result) <= 50

    def test_empty(self):
        assert slugify_title("") == "misc"

    def test_no_hash_prefix(self):
        assert slugify_title("Just a title") == "just-a-title"


class TestExtractTitle:
    def test_extracts_h1(self):
        md = "# Session Title\n\nSome content"
        assert extract_title(md) == "# Session Title"

    def test_skips_h2(self):
        md = "## Not this\n# This one\nContent"
        assert extract_title(md) == "# This one"

    def test_no_title(self):
        assert extract_title("No title here") == "# Untitled Session"

    def test_title_with_leading_whitespace(self):
        md = "  # Spaced Title\nContent"
        assert extract_title(md) == "# Spaced Title"


class TestCountUserTurns:
    def test_counts_all(self, transcript):
        assert count_user_turns(transcript) == 6

    def test_counts_from_start_line(self, transcript):
        # Skip first 4 entries (2 user, 2 assistant) → 4 user turns remain
        assert count_user_turns(transcript, start_line=4) == 4

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        assert count_user_turns(path) == 0


class TestFindSummary:
    def test_finds_by_session_id(self, vault_dir):
        vault_dir.mkdir(parents=True)
        f = vault_dir / "2026-02-10-abc12345.md"
        f.write_text("# Test")
        assert find_summary(vault_dir, "abc12345-full-uuid") == f

    def test_finds_in_sessions_subfolder(self, vault_dir):
        vault_dir.mkdir(parents=True)
        week = vault_dir / "sessions" / "2026-W07"
        week.mkdir(parents=True)
        f = week / "2026-02-09-test-abc12345.md"
        f.write_text("# Test")
        assert find_summary(vault_dir, "abc12345-full-uuid") == f

    def test_sessions_preferred_over_root(self, vault_dir):
        """Sessions dir is checked first, root is fallback."""
        vault_dir.mkdir(parents=True)
        week = vault_dir / "sessions" / "2026-W07"
        week.mkdir(parents=True)
        f_sessions = week / "2026-02-09-test-abc12345.md"
        f_sessions.write_text("# In sessions")
        f_root = vault_dir / "2026-02-09-abc12345.md"
        f_root.write_text("# In root")
        result = find_summary(vault_dir, "abc12345-full-uuid")
        assert "sessions" in str(result)

    def test_returns_none_when_missing(self, vault_dir):
        vault_dir.mkdir(parents=True)
        assert find_summary(vault_dir, "nonexistent") is None

    def test_returns_none_when_dir_missing(self, tmp_path):
        assert find_summary(tmp_path / "nope", "abc") is None


class TestValidateFrontmatter:
    def test_valid_frontmatter_passes_through(self):
        text = "---\nsession: abc\nconcepts: [hooks, tdd]\n---\n# Title\nContent"
        result = validate_frontmatter(text)
        assert result == text

    def test_missing_frontmatter_injected(self):
        text = "# Title\nContent"
        result = validate_frontmatter(text)
        assert result.startswith("---\n")
        assert "concepts: []\n" in result
        assert "# Title\nContent" in result

    def test_malformed_yaml_rebuilt(self):
        text = "---\n: bad yaml\n---\n# Title\nContent"
        result = validate_frontmatter(text)
        assert result.startswith("---\n")
        assert "concepts: []\n" in result
        assert "# Title\nContent" in result

    def test_concepts_string_converted_to_list(self):
        text = "---\nconcepts: hooks\n---\n# Title"
        result = validate_frontmatter(text)
        assert "concepts: [hooks]" in result

    def test_preserves_other_fields(self):
        text = "---\nsession: abc\ndate: 2026-02-09\nconcepts: [hooks]\n---\n# Title"
        result = validate_frontmatter(text)
        assert "session: abc" in result
        assert "date: '2026-02-09'" in result or "date: 2026-02-09" in result

    def test_strips_llm_preamble_before_frontmatter(self):
        text = (
            "An updated session summary based on the new content has been generated.\n\n"
            "**Updated Summary:**\n"
            "---\nsession: abc\nconcepts: [hooks]\n---\n# Title\nContent"
        )
        result = validate_frontmatter(text)
        assert "session: abc" in result
        assert "Updated Summary" not in result
        assert result.startswith("---\n")

    def test_strips_markdown_code_fences(self):
        text = "```markdown\n---\nsession: abc\nconcepts: [hooks]\n---\n# Title\n```"
        result = validate_frontmatter(text)
        assert "session: abc" in result
        assert "```" not in result

    def test_finds_buried_frontmatter_when_stub_first(self):
        """The exact d2734c0a failure mode: stub frontmatter, real one buried in body."""
        text = (
            "---\nconcepts: []\n---\n"
            "An updated session summary.\n\n"
            "---\nsession: abc\ndate: 2026-02-10\nweek: 7\n"
            "concepts: [ai-defensibility, bottleneck-migration]\n"
            "summary: >-\n  We started by synthesizing.\n"
            "---\n# Finding the Axes\n\nContent here."
        )
        result = validate_frontmatter(text)
        assert "session: abc" in result
        assert "ai-defensibility" in result
        assert result.startswith("---\n")
        assert "# Finding the Axes" in result

    def test_strips_junk_fields_from_frontmatter(self):
        text = (
            "---\nsession: abc\nconcepts: [hooks]\n"
            "title: Some Title\nrole: note\ntype: note\nstatus: new\n"
            "tags: []\nlinks: []\ntopics: [a, b]\n"
            "---\n# Title\nContent"
        )
        result = validate_frontmatter(text)
        assert "role:" not in result
        assert "type:" not in result
        assert "status:" not in result
        assert "tags:" not in result
        assert "links:" not in result
        assert "topics:" not in result
        assert "session: abc" in result

    def test_concepts_comma_string_split(self):
        text = "---\nsession: abc\nconcepts: hooks, tdd, vault\n---\n# Title"
        result = validate_frontmatter(text)
        assert "hooks" in result
        assert "tdd" in result
        assert "vault" in result


class TestSummarizeBase:
    @patch("formaltask.vault.summarizer._get_client")
    def test_returns_content_with_frontmatter(self, mock_get):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="---\nconcepts: [hooks]\n---\n# Title\n\nSummary"))
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get.return_value = (mock_client, "model")

        result = summarize_base(
            "x" * 300, session_id="abc12345", date_str="2026-02-09", week_str="2026-W07"
        )
        assert "# Title" in result
        assert "concepts:" in result

    @patch("formaltask.vault.summarizer._get_client")
    def test_passes_concepts_in_user_message(self, mock_get):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="---\nconcepts: [hooks]\n---\n# Title"))
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get.return_value = (mock_client, "model")

        summarize_base("x" * 300, concepts=["hooks", "tdd"])
        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        assert "hooks" in user_msg and "tdd" in user_msg

    @patch("formaltask.vault.summarizer._get_client")
    def test_passes_session_metadata_in_user_message(self, mock_get):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="---\nconcepts: [hooks]\n---\n# Title"))
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get.return_value = (mock_client, "model")

        summarize_base("x" * 300, session_id="abc12345", date_str="2026-02-09", week_str="2026-W07")
        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        assert "abc12345" in user_msg
        assert "2026-02-09" in user_msg
        assert "2026-W07" in user_msg

    def test_short_segment_returns_none(self):
        assert summarize_base("short") is None

    @patch(
        "formaltask.vault.summarizer._get_client",
        side_effect=openai.APIConnectionError(request=None),
    )
    def test_failure_returns_none(self, mock_get):
        assert summarize_base("x" * 300) is None


class TestSummarizeUpdate:
    @patch("formaltask.vault.summarizer._get_client")
    def test_returns_updated_content(self, mock_get):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="---\nconcepts: [hooks]\n---\n# Updated\n\nNew stuff")
            )
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get.return_value = (mock_client, "model")

        result = summarize_update("# Old\n\nOld stuff", "x" * 300, concepts=["hooks"])
        assert "# Updated" in result

    @patch("formaltask.vault.summarizer._get_client")
    def test_passes_concepts_in_user_message(self, mock_get):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="---\nconcepts: [hooks]\n---\n# Updated"))
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get.return_value = (mock_client, "model")

        summarize_update("# Old", "x" * 300, concepts=["hooks", "tdd"])
        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        assert "EXISTING CONCEPTS:" in user_msg

    def test_short_segment_returns_none(self):
        assert summarize_update("# Old", "short") is None

    @patch(
        "formaltask.vault.summarizer._get_client",
        side_effect=openai.APIConnectionError(request=None),
    )
    def test_failure_returns_none(self, mock_get):
        assert summarize_update("# Old", "x" * 300) is None
