"""Tests for session_start phases."""

import json


class TestRunSessionFile:
    """Load handoff context on session start."""

    def test_loads_handoff_from_session_name(self, tmp_path):
        """Detects .session/name and loads previous handoff."""
        from hooks.session_start.phases import run_session_file

        # Set up directory structure
        handoffs_dir = tmp_path / "handoffs"
        projects_dir = tmp_path / "projects"

        # Create .session/name file in cwd
        cwd = tmp_path / "session-worktree"
        cwd.mkdir()
        session_dir = cwd / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("my-session")

        # Create handoff file
        thread_dir = handoffs_dir / "my-session"
        thread_dir.mkdir(parents=True)
        handoff_path = thread_dir / "01--2026-02-02--initial-work.md"
        handoff_content = "# my-session Handoff #1\n\nPrevious session context."
        handoff_path.write_text(handoff_content)

        # Create thread index
        index_path = handoffs_dir / "thread-index.json"
        index_path.write_text(
            json.dumps({"my-session": ["my-session/01--2026-02-02--initial-work.md"]})
        )

        ctx = {"cwd": str(cwd)}
        result = run_session_file(ctx, projects_dir=projects_dir, handoff_dir=handoffs_dir)

        assert result is not None
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in result["hookSpecificOutput"]
        assert "my-session" in result["hookSpecificOutput"]["additionalContext"]
        assert "Previous session context" in result["hookSpecificOutput"]["additionalContext"]

    def test_session_name_takes_priority_over_breadcrumb(self, tmp_path):
        """When both exist, .session/name takes priority over breadcrumb."""
        from hooks.session_start.phases import run_session_file

        # Set up directory structure
        handoffs_dir = tmp_path / "handoffs"
        projects_dir = tmp_path / "projects"

        # Create .session/name file in cwd
        cwd = tmp_path / "session-worktree"
        cwd.mkdir()
        session_dir = cwd / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("session-thread")

        # Create session handoff
        session_thread_dir = handoffs_dir / "session-thread"
        session_thread_dir.mkdir(parents=True)
        session_handoff = session_thread_dir / "01--2026-02-02--session.md"
        session_handoff.write_text("Session handoff content.")

        # Create breadcrumb pointing to different thread
        project_id = "test-project"
        breadcrumb_dir = projects_dir / project_id
        breadcrumb_dir.mkdir(parents=True)
        (breadcrumb_dir / "handoff-thread.txt").write_text("breadcrumb-thread")

        # Create breadcrumb handoff
        breadcrumb_thread_dir = handoffs_dir / "breadcrumb-thread"
        breadcrumb_thread_dir.mkdir(parents=True)
        breadcrumb_handoff = breadcrumb_thread_dir / "01--2026-02-02--breadcrumb.md"
        breadcrumb_handoff.write_text("Breadcrumb handoff content.")

        # Create thread index
        index_path = handoffs_dir / "thread-index.json"
        index_path.write_text(
            json.dumps({
                "session-thread": ["session-thread/01--2026-02-02--session.md"],
                "breadcrumb-thread": ["breadcrumb-thread/01--2026-02-02--breadcrumb.md"],
            })
        )

        ctx = {"cwd": str(cwd), "project_id": project_id}
        result = run_session_file(ctx, projects_dir=projects_dir, handoff_dir=handoffs_dir)

        assert result is not None
        # Should use session-thread, not breadcrumb-thread
        assert "session-thread" in result["hookSpecificOutput"]["additionalContext"]
        assert "Session handoff content" in result["hookSpecificOutput"]["additionalContext"]
        assert "breadcrumb-thread" not in result["hookSpecificOutput"]["additionalContext"]

    def test_falls_back_to_breadcrumb_when_no_session_name(self, tmp_path):
        """Falls back to breadcrumb when .session/name doesn't exist."""
        from hooks.session_start.phases import run_session_file

        # Set up directory structure
        projects_dir = tmp_path / "projects"
        handoffs_dir = tmp_path / "handoffs"

        # Create breadcrumb pointing to thread
        project_id = "test-project-123"
        breadcrumb_dir = projects_dir / project_id
        breadcrumb_dir.mkdir(parents=True)
        (breadcrumb_dir / "handoff-thread.txt").write_text("auth-refactor")

        # Create handoff file
        thread_dir = handoffs_dir / "auth-refactor"
        thread_dir.mkdir(parents=True)
        handoff_path = thread_dir / "01--2026-02-02--designing-tokens.md"
        handoff_content = "# auth-refactor Handoff #1\n\nTest content."
        handoff_path.write_text(handoff_content)

        # Create thread index
        index_path = handoffs_dir / "thread-index.json"
        index_path.write_text(
            json.dumps({"auth-refactor": ["auth-refactor/01--2026-02-02--designing-tokens.md"]})
        )

        ctx = {"project_id": project_id}
        result = run_session_file(ctx, projects_dir=projects_dir, handoff_dir=handoffs_dir)

        assert result is not None
        assert "hookSpecificOutput" in result
        assert "additionalContext" in result["hookSpecificOutput"]
        assert "auth-refactor" in result["hookSpecificOutput"]["additionalContext"]
        assert "Test content" in result["hookSpecificOutput"]["additionalContext"]

    def test_returns_none_when_no_breadcrumb(self, tmp_path):
        """No breadcrumb file returns None."""
        from hooks.session_start.phases import run_session_file

        projects_dir = tmp_path / "projects"
        handoffs_dir = tmp_path / "handoffs"

        # Create project dir but no breadcrumb
        project_dir = projects_dir / "test-project"
        project_dir.mkdir(parents=True)

        ctx = {"project_id": "test-project"}
        result = run_session_file(ctx, projects_dir=projects_dir, handoff_dir=handoffs_dir)

        assert result is None

    def test_returns_none_when_no_project_id_and_no_session(self, tmp_path):
        """No project_id and no .session/name returns None."""
        from hooks.session_start.phases import run_session_file

        projects_dir = tmp_path / "projects"
        handoffs_dir = tmp_path / "handoffs"

        ctx = {}
        result = run_session_file(ctx, projects_dir=projects_dir, handoff_dir=handoffs_dir)

        assert result is None

    def test_returns_none_when_no_handoff_exists(self, tmp_path):
        """Breadcrumb exists but no handoff returns None."""
        from hooks.session_start.phases import run_session_file

        projects_dir = tmp_path / "projects"
        handoffs_dir = tmp_path / "handoffs"

        # Create breadcrumb
        project_id = "test-project"
        breadcrumb_dir = projects_dir / project_id
        breadcrumb_dir.mkdir(parents=True)
        (breadcrumb_dir / "handoff-thread.txt").write_text("nonexistent-thread")

        # Create empty index (no handoffs for this thread)
        handoffs_dir.mkdir(parents=True)
        (handoffs_dir / "thread-index.json").write_text(json.dumps({}))

        ctx = {"project_id": project_id}
        result = run_session_file(ctx, projects_dir=projects_dir, handoff_dir=handoffs_dir)

        assert result is None

    def test_session_name_no_handoff_falls_through_to_breadcrumb(self, tmp_path):
        """If .session/name exists but has no handoff, checks breadcrumb."""
        from hooks.session_start.phases import run_session_file

        # Set up directory structure
        handoffs_dir = tmp_path / "handoffs"
        projects_dir = tmp_path / "projects"

        # Create .session/name file but no handoff for it
        cwd = tmp_path / "session-worktree"
        cwd.mkdir()
        session_dir = cwd / ".session"
        session_dir.mkdir()
        (session_dir / "name").write_text("no-handoff-session")

        # Create breadcrumb pointing to thread WITH handoff
        project_id = "test-project"
        breadcrumb_dir = projects_dir / project_id
        breadcrumb_dir.mkdir(parents=True)
        (breadcrumb_dir / "handoff-thread.txt").write_text("breadcrumb-thread")

        # Create breadcrumb handoff
        breadcrumb_thread_dir = handoffs_dir / "breadcrumb-thread"
        breadcrumb_thread_dir.mkdir(parents=True)
        breadcrumb_handoff = breadcrumb_thread_dir / "01--2026-02-02--breadcrumb.md"
        breadcrumb_handoff.write_text("Breadcrumb handoff content.")

        # Create thread index (only has breadcrumb-thread)
        index_path = handoffs_dir / "thread-index.json"
        index_path.write_text(
            json.dumps({
                "breadcrumb-thread": ["breadcrumb-thread/01--2026-02-02--breadcrumb.md"],
            })
        )

        ctx = {"cwd": str(cwd), "project_id": project_id}
        result = run_session_file(ctx, projects_dir=projects_dir, handoff_dir=handoffs_dir)

        # Falls through to breadcrumb since session has no handoff
        assert result is not None
        assert "breadcrumb-thread" in result["hookSpecificOutput"]["additionalContext"]
