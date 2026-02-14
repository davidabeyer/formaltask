"""Tests for vault concepts — concept cache, weekly folders, index pages."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from formaltask.vault.concepts import (
    generate_session_index,
    get_concept_list,
    get_week_folder,
    materialize_concepts,
    migrate_vault,
    parse_frontmatter,
    parse_frontmatter_concepts,
    update_concept_cache,
)


@pytest.fixture
def vault_dir(tmp_path):
    d = tmp_path / "vault"
    d.mkdir()
    return d


class TestGetWeekFolder:
    def test_returns_correct_iso_week(self, vault_dir):
        d = date(2026, 2, 9)  # Monday of week 7
        result = get_week_folder(vault_dir, d)
        assert result == vault_dir / "sessions" / "2026-W07"

    def test_creates_directory(self, vault_dir):
        d = date(2026, 1, 5)  # Week 2
        result = get_week_folder(vault_dir, d)
        assert result.is_dir()

    def test_week_1(self, vault_dir):
        d = date(2026, 1, 1)  # Thursday, ISO week 1
        result = get_week_folder(vault_dir, d)
        assert result.name == "2026-W01"


class TestParseFrontmatterConcepts:
    def test_valid_yaml(self):
        text = "---\nsession: abc\nconcepts: [mcp-servers, vault-design]\n---\n# Title"
        assert parse_frontmatter_concepts(text) == ["mcp-servers", "vault-design"]

    def test_no_frontmatter(self):
        assert parse_frontmatter_concepts("# Just a title\nContent") == []

    def test_empty_concepts(self):
        text = "---\nsession: abc\nconcepts: []\n---\n# Title"
        assert parse_frontmatter_concepts(text) == []

    def test_malformed_yaml(self):
        text = "---\n: bad: yaml: here\n---\n# Title"
        assert parse_frontmatter_concepts(text) == []

    def test_no_concepts_key(self):
        text = "---\nsession: abc\ndate: 2026-02-09\n---\n# Title"
        assert parse_frontmatter_concepts(text) == []

    def test_concepts_as_string(self):
        """If LLM outputs concepts as a string, still extract."""
        text = "---\nconcepts: mcp-servers\n---\n# Title"
        result = parse_frontmatter_concepts(text)
        assert result == ["mcp-servers"]


class TestGetConceptList:
    def test_reads_cache(self, vault_dir):
        cache = vault_dir / ".concepts.txt"
        cache.write_text("mcp-servers\nvault-design\ntdd\n")
        assert get_concept_list(vault_dir) == ["mcp-servers", "tdd", "vault-design"]

    def test_fallback_to_grep(self, vault_dir):
        """No cache → grep session files for concepts."""
        sessions = vault_dir / "sessions" / "2026-W07"
        sessions.mkdir(parents=True)
        md = sessions / "2026-02-09-test-abc1.md"
        md.write_text("---\nconcepts: [mcp-servers, hooks]\n---\n# Test")
        result = get_concept_list(vault_dir)
        assert "mcp-servers" in result
        assert "hooks" in result

    def test_empty_vault(self, vault_dir):
        assert get_concept_list(vault_dir) == []


class TestUpdateConceptCache:
    def test_creates_cache(self, vault_dir):
        update_concept_cache(vault_dir, ["tdd", "hooks"])
        cache = vault_dir / ".concepts.txt"
        assert cache.exists()
        lines = cache.read_text().strip().split("\n")
        assert lines == ["hooks", "tdd"]

    def test_merges_and_deduplicates(self, vault_dir):
        cache = vault_dir / ".concepts.txt"
        cache.write_text("hooks\nmcp-servers\n")
        update_concept_cache(vault_dir, ["hooks", "tdd"])
        lines = cache.read_text().strip().split("\n")
        assert lines == ["hooks", "mcp-servers", "tdd"]

    def test_empty_new_concepts(self, vault_dir):
        cache = vault_dir / ".concepts.txt"
        cache.write_text("hooks\n")
        update_concept_cache(vault_dir, [])
        assert cache.read_text().strip() == "hooks"


class TestMaterializeConcepts:
    def test_generates_index_pages(self, vault_dir):
        # Set up sessions with frontmatter
        week = vault_dir / "sessions" / "2026-W07"
        week.mkdir(parents=True)
        (week / "2026-02-09-test-abc1.md").write_text(
            "---\nconcepts: [mcp-servers, hooks]\ndate: 2026-02-09\n---\n# MCP Setup"
        )
        (week / "2026-02-10-other-def2.md").write_text(
            "---\nconcepts: [mcp-servers]\ndate: 2026-02-10\n---\n# MCP Fixes"
        )
        cache = vault_dir / ".concepts.txt"
        cache.write_text("hooks\nmcp-servers\n")

        pages = vault_dir / "pages"
        pages.mkdir()

        materialize_concepts(vault_dir)

        mcp_page = pages / "mcp-servers.md"
        assert mcp_page.exists()
        content = mcp_page.read_text()
        assert "MCP Setup" in content
        assert "MCP Fixes" in content

        hooks_page = pages / "hooks.md"
        assert hooks_page.exists()
        assert "MCP Setup" in hooks_page.read_text()

    def test_empty_concepts(self, vault_dir):
        (vault_dir / "pages").mkdir()
        (vault_dir / ".concepts.txt").write_text("")
        materialize_concepts(vault_dir)
        # No pages generated (besides any pre-existing)
        assert list((vault_dir / "pages").glob("*.md")) == []


class TestParseFrontmatter:
    def test_returns_full_dict(self):
        text = "---\nsession: abc\ndate: 2026-02-09\nsummary: Built vault system.\nconcepts: [vault]\n---\n# Title"
        fm = parse_frontmatter(text)
        assert fm["session"] == "abc"
        assert fm["summary"] == "Built vault system."
        assert fm["concepts"] == ["vault"]

    def test_no_frontmatter_returns_empty(self):
        assert parse_frontmatter("# Just a title") == {}

    def test_malformed_yaml_returns_empty(self):
        assert parse_frontmatter("---\n: bad\n---\n# Title") == {}

    def test_non_dict_frontmatter_returns_empty(self):
        assert parse_frontmatter("---\n- list item\n---\n# Title") == {}


class TestGenerateSessionIndex:
    def _make_session(self, vault_dir, week, filename, title, date_str, summary=""):
        week_dir = vault_dir / "sessions" / week
        week_dir.mkdir(parents=True, exist_ok=True)
        fm_lines = [
            "---",
            f"date: {date_str}",
            f"summary: {summary}" if summary else "summary: ''",
            "concepts: [test]",
            "---",
            f"# {title}",
            "",
            "Content here.",
        ]
        (week_dir / filename).write_text("\n".join(fm_lines))

    def test_generates_index_newest_first(self, vault_dir):
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        self._make_session(vault_dir, "2026-W06", f"{two_days_ago}-old-abc1.md",
                           "Old Session", str(two_days_ago), "We did old stuff.")
        self._make_session(vault_dir, "2026-W07", f"{yesterday}-new-def2.md",
                           "New Session", str(yesterday), "We did new stuff.")

        generate_session_index(vault_dir)

        index = vault_dir / "INDEX.md"
        assert index.exists()
        content = index.read_text()
        # New session should appear before old session
        new_pos = content.index("New Session")
        old_pos = content.index("Old Session")
        assert new_pos < old_pos

    def test_includes_summary_text(self, vault_dir):
        today = str(date.today())
        self._make_session(vault_dir, "2026-W07", f"{today}-test-abc1.md",
                           "Test Session", today, "We built the vault memory layers.")

        generate_session_index(vault_dir)

        content = (vault_dir / "INDEX.md").read_text()
        assert "We built the vault memory layers." in content

    def test_includes_session_title_as_link(self, vault_dir):
        today = str(date.today())
        self._make_session(vault_dir, "2026-W07", f"{today}-test-abc1.md",
                           "Test Session", today, "Summary.")

        generate_session_index(vault_dir)

        content = (vault_dir / "INDEX.md").read_text()
        assert "[Test Session]" in content
        assert f"sessions/2026-W07/{today}-test-abc1.md" in content

    def test_empty_vault_no_crash(self, vault_dir):
        generate_session_index(vault_dir)
        assert not (vault_dir / "INDEX.md").exists()

    def test_no_sessions_dir_no_crash(self, vault_dir):
        generate_session_index(vault_dir)

    def test_missing_summary_still_listed(self, vault_dir):
        today = str(date.today())
        self._make_session(vault_dir, "2026-W07", f"{today}-test-abc1.md",
                           "No Summary Session", today)

        generate_session_index(vault_dir)

        content = (vault_dir / "INDEX.md").read_text()
        assert "No Summary Session" in content

    def test_excludes_sessions_older_than_two_weeks(self, vault_dir):
        today = date.today()
        recent = str(today - timedelta(days=3))
        old = str(today - timedelta(days=20))
        self._make_session(vault_dir, "2026-W07", f"{recent}-new-abc1.md",
                           "Recent Session", recent, "Recent work.")
        self._make_session(vault_dir, "2026-W04", f"{old}-old-def2.md",
                           "Old Session", old, "Old work.")

        generate_session_index(vault_dir)

        content = (vault_dir / "INDEX.md").read_text()
        assert "Recent Session" in content
        assert "Old Session" not in content


class TestMigrateVault:
    def test_moves_file_to_week_folder(self, vault_dir):
        """Session file at root moves to sessions/{week}/."""
        f = vault_dir / "2026-02-09-abc12345.md"
        f.write_text("# Auth Flow\nContent here.")
        migrate_vault(vault_dir)

        assert not f.exists()
        week = vault_dir / "sessions" / "2026-W07"
        dest = week / "2026-02-09-abc12345.md"
        assert dest.exists()
        assert "Auth Flow" in dest.read_text()

    def test_injects_frontmatter(self, vault_dir):
        """Files without frontmatter get minimal YAML injected."""
        f = vault_dir / "2026-02-09-abc12345.md"
        f.write_text("# Auth Flow\nContent here.")
        migrate_vault(vault_dir)

        week = vault_dir / "sessions" / "2026-W07"
        text = (week / "2026-02-09-abc12345.md").read_text()
        assert text.startswith("---\n")
        assert "session: abc12345" in text
        assert "date: 2026-02-09" in text
        assert "week: 2026-W07" in text
        assert "concepts: []" in text
        assert "# Auth Flow" in text

    def test_preserves_existing_frontmatter(self, vault_dir):
        """Files with frontmatter don't get double-wrapped."""
        f = vault_dir / "2026-02-09-abc12345.md"
        f.write_text("---\nconcepts: [hooks]\n---\n# Auth Flow\nContent.")
        migrate_vault(vault_dir)

        week = vault_dir / "sessions" / "2026-W07"
        text = (week / "2026-02-09-abc12345.md").read_text()
        # Should start with original frontmatter, not doubled
        assert text.count("---") == 2
        assert "concepts: [hooks]" in text

    def test_deletes_legacy_config(self, vault_dir):
        """.schema.yaml and .tag-aliases.yaml get deleted."""
        (vault_dir / ".schema.yaml").write_text("schema: v1")
        (vault_dir / ".tag-aliases.yaml").write_text("aliases: {}")
        migrate_vault(vault_dir)

        assert not (vault_dir / ".schema.yaml").exists()
        assert not (vault_dir / ".tag-aliases.yaml").exists()

    def test_skips_non_session_files(self, vault_dir):
        """Files not matching YYYY-MM-DD-*.md pattern are left alone."""
        f = vault_dir / "random-notes.md"
        f.write_text("# Random")
        migrate_vault(vault_dir)

        assert f.exists()  # Not moved

    def test_empty_vault(self, vault_dir):
        """Empty vault dir doesn't crash."""
        migrate_vault(vault_dir)

    def test_missing_vault_dir(self, tmp_path):
        """Non-existent vault dir doesn't crash."""
        migrate_vault(tmp_path / "nope")
