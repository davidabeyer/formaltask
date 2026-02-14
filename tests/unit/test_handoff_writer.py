"""Tests for handoff file output with thread indexing."""

import json
from datetime import datetime


class TestSlugify:
    """Slugify converts summary text to filesystem-safe slugs."""

    def test_lowercases_text(self):
        """Uppercase letters become lowercase."""
        from hooks.pre_compact.handoff_writer import slugify

        assert slugify("Hello World") == "hello-world"

    def test_replaces_spaces_with_hyphens(self):
        """Spaces become hyphens."""
        from hooks.pre_compact.handoff_writer import slugify

        assert slugify("designing jwt tokens") == "designing-jwt-tokens"

    def test_removes_special_characters(self):
        """Non-alphanumeric chars (except hyphens) are removed."""
        from hooks.pre_compact.handoff_writer import slugify

        assert slugify("What's the plan?") == "whats-the-plan"

    def test_collapses_multiple_hyphens(self):
        """Multiple consecutive hyphens become single hyphen."""
        from hooks.pre_compact.handoff_writer import slugify

        assert slugify("hello   world") == "hello-world"
        assert slugify("hello---world") == "hello-world"

    def test_strips_leading_trailing_hyphens(self):
        """Leading and trailing hyphens are removed."""
        from hooks.pre_compact.handoff_writer import slugify

        assert slugify("  hello world  ") == "hello-world"
        assert slugify("--hello--") == "hello"

    def test_truncates_long_slugs(self):
        """Slugs are truncated to reasonable length (50 chars)."""
        from hooks.pre_compact.handoff_writer import slugify

        long_text = "this is a very long summary that should be truncated to avoid filesystem issues"
        result = slugify(long_text)
        assert len(result) <= 50

    def test_handles_empty_string(self):
        """Empty string returns 'untitled'."""
        from hooks.pre_compact.handoff_writer import slugify

        assert slugify("") == "untitled"
        assert slugify("   ") == "untitled"


class TestGetNextSequence:
    """Get sequence number for next handoff in a thread directory."""

    def test_returns_1_for_empty_directory(self, tmp_path):
        """First handoff in thread gets sequence 1."""
        from hooks.pre_compact.handoff_writer import get_next_sequence

        thread_dir = tmp_path / "auth-refactor"
        thread_dir.mkdir()

        assert get_next_sequence(thread_dir) == 1

    def test_returns_1_for_nonexistent_directory(self, tmp_path):
        """Nonexistent thread directory returns 1."""
        from hooks.pre_compact.handoff_writer import get_next_sequence

        thread_dir = tmp_path / "new-thread"
        # Don't create it

        assert get_next_sequence(thread_dir) == 1

    def test_increments_from_existing_files(self, tmp_path):
        """Returns next number after highest existing sequence."""
        from hooks.pre_compact.handoff_writer import get_next_sequence

        thread_dir = tmp_path / "auth-refactor"
        thread_dir.mkdir()
        (thread_dir / "01--2026-02-02--designing-jwt-tokens.md").touch()
        (thread_dir / "02--2026-02-02--refresh-token-flow.md").touch()

        assert get_next_sequence(thread_dir) == 3

    def test_handles_gaps_in_sequence(self, tmp_path):
        """Uses highest number even with gaps."""
        from hooks.pre_compact.handoff_writer import get_next_sequence

        thread_dir = tmp_path / "auth-refactor"
        thread_dir.mkdir()
        (thread_dir / "01--2026-02-02--first.md").touch()
        (thread_dir / "05--2026-02-02--fifth.md").touch()

        assert get_next_sequence(thread_dir) == 6

    def test_ignores_non_matching_files(self, tmp_path):
        """Files not matching pattern are ignored."""
        from hooks.pre_compact.handoff_writer import get_next_sequence

        thread_dir = tmp_path / "auth-refactor"
        thread_dir.mkdir()
        (thread_dir / "01--2026-02-02--first.md").touch()
        (thread_dir / "README.md").touch()
        (thread_dir / "notes.txt").touch()

        assert get_next_sequence(thread_dir) == 2


class TestWriteHandoff:
    """Write handoff files to thread-first directories."""

    def test_creates_thread_directory_structure(self, tmp_path):
        """Creates thread-name/ directory with sequence-numbered files."""
        from hooks.pre_compact.handoff_writer import write_handoff

        content = {"summary": "Test handoff", "decisions": [], "completed": [], "pending": [], "context": "", "files_touched": []}

        filepath = write_handoff("test-thread", content, handoff_dir=tmp_path)

        assert filepath.exists()
        # Parent should be thread directory
        assert filepath.parent.name == "test-thread"
        assert filepath.parent.parent == tmp_path

    def test_filename_includes_sequence_date_and_summary(self, tmp_path):
        """Filename is NN--YYYY-MM-DD--summary-slug.md."""
        from hooks.pre_compact.handoff_writer import write_handoff

        content = {"summary": "Designing JWT tokens", "decisions": [], "completed": [], "pending": [], "context": "", "files_touched": []}

        filepath = write_handoff("auth-refactor", content, handoff_dir=tmp_path)

        # Check format: NN--YYYY-MM-DD--summary-slug.md
        assert filepath.name.startswith("01--")
        assert datetime.now().strftime("%Y-%m-%d") in filepath.name
        assert "designing-jwt-tokens" in filepath.name
        assert filepath.suffix == ".md"

    def test_increments_sequence_number(self, tmp_path):
        """Subsequent handoffs get incremented sequence numbers."""
        from hooks.pre_compact.handoff_writer import write_handoff

        content1 = {"summary": "First handoff", "decisions": [], "completed": [], "pending": [], "context": "", "files_touched": []}
        content2 = {"summary": "Second handoff", "decisions": [], "completed": [], "pending": [], "context": "", "files_touched": []}

        filepath1 = write_handoff("auth-refactor", content1, handoff_dir=tmp_path)
        filepath2 = write_handoff("auth-refactor", content2, handoff_dir=tmp_path)

        assert filepath1.name.startswith("01--")
        assert filepath2.name.startswith("02--")

    def test_writes_markdown_content(self, tmp_path):
        """Writes structured markdown with all fields."""
        from hooks.pre_compact.handoff_writer import write_handoff

        content = {
            "summary": "Refactored auth system.",
            "decisions": ["Use JWT tokens", "Expire after 24h"],
            "completed": ["Token generation", "Token validation"],
            "pending": ["Refresh token flow"],
            "context": "Working on ticket AUTH-123",
            "files_touched": ["src/auth.py", "src/tokens.py"],
        }

        filepath = write_handoff("auth-refactor", content, handoff_dir=tmp_path)
        text = filepath.read_text()

        assert "# auth-refactor Handoff" in text
        assert "Refactored auth system." in text
        assert "Use JWT tokens" in text
        assert "Expire after 24h" in text
        assert "Token generation" in text
        assert "Refresh token flow" in text
        assert "Working on ticket AUTH-123" in text
        assert "src/auth.py" in text

    def test_handles_empty_lists(self, tmp_path):
        """Empty lists produce empty sections gracefully."""
        from hooks.pre_compact.handoff_writer import write_handoff

        content = {
            "summary": "Quick fix",
            "decisions": [],
            "completed": ["Fixed bug"],
            "pending": [],
            "context": "",
            "files_touched": [],
        }

        filepath = write_handoff("quick-fix", content, handoff_dir=tmp_path)
        text = filepath.read_text()

        assert "Quick fix" in text
        assert "Fixed bug" in text


class TestUpdateThreadIndex:
    """Thread index tracks all handoffs for a thread."""

    def test_creates_index_if_not_exists(self, tmp_path):
        """Creates thread-index.json if it doesn't exist."""
        from hooks.pre_compact.handoff_writer import update_thread_index

        update_thread_index("test-thread", "test-thread/01--2026-02-02--initial.md", handoff_dir=tmp_path)

        index_file = tmp_path / "thread-index.json"
        assert index_file.exists()
        data = json.loads(index_file.read_text())
        assert "test-thread" in data
        assert data["test-thread"][-1] == "test-thread/01--2026-02-02--initial.md"

    def test_appends_to_existing_thread(self, tmp_path):
        """Adds new handoff to existing thread history."""
        from hooks.pre_compact.handoff_writer import update_thread_index

        index_file = tmp_path / "thread-index.json"
        index_file.write_text(json.dumps({"test-thread": ["test-thread/01--2026-02-01--first.md"]}))

        update_thread_index("test-thread", "test-thread/02--2026-02-02--second.md", handoff_dir=tmp_path)

        data = json.loads(index_file.read_text())
        assert len(data["test-thread"]) == 2
        assert data["test-thread"][1] == "test-thread/02--2026-02-02--second.md"

    def test_creates_new_thread_entry(self, tmp_path):
        """Creates new thread entry in existing index."""
        from hooks.pre_compact.handoff_writer import update_thread_index

        index_file = tmp_path / "thread-index.json"
        index_file.write_text(json.dumps({"other-thread": ["other-thread/01--2026-02-01--first.md"]}))

        update_thread_index("new-thread", "new-thread/01--2026-02-02--initial.md", handoff_dir=tmp_path)

        data = json.loads(index_file.read_text())
        assert "other-thread" in data
        assert "new-thread" in data


class TestFindPrevHandoff:
    """Find previous handoff for thread continuity."""

    def test_returns_most_recent_handoff(self, tmp_path):
        """Returns the last handoff path for a thread."""
        from hooks.pre_compact.handoff_writer import find_prev_handoff

        index_file = tmp_path / "thread-index.json"
        index_file.write_text(json.dumps({
            "test-thread": [
                "test-thread/01--2026-02-01--first.md",
                "test-thread/02--2026-02-02--second.md",
            ]
        }))

        result = find_prev_handoff("test-thread", handoff_dir=tmp_path)

        assert result == "test-thread/02--2026-02-02--second.md"

    def test_returns_none_for_unknown_thread(self, tmp_path):
        """Unknown thread returns None."""
        from hooks.pre_compact.handoff_writer import find_prev_handoff

        index_file = tmp_path / "thread-index.json"
        index_file.write_text(json.dumps({"other-thread": ["other-thread/01--2026-02-01--first.md"]}))

        result = find_prev_handoff("unknown-thread", handoff_dir=tmp_path)

        assert result is None

    def test_returns_none_if_no_index(self, tmp_path):
        """No index file returns None."""
        from hooks.pre_compact.handoff_writer import find_prev_handoff

        result = find_prev_handoff("any-thread", handoff_dir=tmp_path)

        assert result is None


class TestWriteStubHandoff:
    """Write stub handoff when API fails."""

    def test_writes_stub_with_error_message(self, tmp_path):
        """Stub contains error and transcript path for manual recovery."""
        from hooks.pre_compact.handoff_writer import write_stub_handoff

        filepath = write_stub_handoff(
            "failed-thread",
            transcript_path="/path/to/session.jsonl",
            error="OpenRouter API timeout",
            handoff_dir=tmp_path,
        )

        assert filepath.exists()
        text = filepath.read_text()
        assert "STUB" in text or "stub" in text
        assert "OpenRouter API timeout" in text
        assert "/path/to/session.jsonl" in text

    def test_stub_uses_thread_directory_structure(self, tmp_path):
        """Stub handoff uses same thread-first directory structure."""
        from hooks.pre_compact.handoff_writer import write_stub_handoff

        filepath = write_stub_handoff(
            "failed-thread",
            transcript_path="/path/to/session.jsonl",
            error="API error",
            handoff_dir=tmp_path,
        )

        # Parent should be thread directory
        assert filepath.parent.name == "failed-thread"
        # Filename should have sequence and STUB marker
        assert filepath.name.startswith("01--")
        assert "STUB" in filepath.name

    def test_stub_updates_thread_index(self, tmp_path):
        """Stub handoff still gets indexed."""
        from hooks.pre_compact.handoff_writer import write_stub_handoff

        write_stub_handoff(
            "stub-thread",
            transcript_path="/path/to/session.jsonl",
            error="API error",
            handoff_dir=tmp_path,
        )

        index_file = tmp_path / "thread-index.json"
        assert index_file.exists()
        data = json.loads(index_file.read_text())
        assert "stub-thread" in data


class TestFormatHandoffMarkdown:
    """Markdown formatter includes sequence number in title."""

    def test_includes_sequence_in_title(self):
        """Title includes sequence number for easy identification."""
        from hooks.pre_compact.handoff_writer import _format_handoff_markdown

        markdown = _format_handoff_markdown("auth-refactor", {"summary": "Test"}, sequence=3)

        assert "# auth-refactor Handoff #3" in markdown

    def test_defaults_to_no_sequence_when_not_provided(self):
        """Backward compatible - no sequence = no number in title."""
        from hooks.pre_compact.handoff_writer import _format_handoff_markdown

        markdown = _format_handoff_markdown("auth-refactor", {"summary": "Test"})

        assert "# auth-refactor Handoff\n" in markdown


class TestWriteThreadBreadcrumb:
    """Write thread breadcrumb for session-start loading."""

    def test_writes_thread_name_to_project_directory(self, tmp_path):
        """Breadcrumb file contains thread name."""
        from hooks.pre_compact.handoff_writer import write_thread_breadcrumb

        projects_dir = tmp_path / "projects"
        project_id = "abc123"

        write_thread_breadcrumb("auth-refactor", project_id, projects_dir=projects_dir)

        breadcrumb = projects_dir / project_id / "handoff-thread.txt"
        assert breadcrumb.exists()
        assert breadcrumb.read_text() == "auth-refactor"

    def test_creates_parent_directories(self, tmp_path):
        """Creates project directory if it doesn't exist."""
        from hooks.pre_compact.handoff_writer import write_thread_breadcrumb

        projects_dir = tmp_path / "projects"
        # Don't create it - let the function create it

        write_thread_breadcrumb("test-thread", "new-project", projects_dir=projects_dir)

        assert (projects_dir / "new-project" / "handoff-thread.txt").exists()

    def test_overwrites_existing_breadcrumb(self, tmp_path):
        """Subsequent calls overwrite the breadcrumb."""
        from hooks.pre_compact.handoff_writer import write_thread_breadcrumb

        projects_dir = tmp_path / "projects"
        project_id = "abc123"

        write_thread_breadcrumb("old-thread", project_id, projects_dir=projects_dir)
        write_thread_breadcrumb("new-thread", project_id, projects_dir=projects_dir)

        breadcrumb = projects_dir / project_id / "handoff-thread.txt"
        assert breadcrumb.read_text() == "new-thread"
