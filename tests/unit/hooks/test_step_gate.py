"""Tests for step_gate PreToolUse hook."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure _HAS_LIFE_DB is True for all tests so check() doesn't short-circuit
_LIFE_DB_PATCH = patch("hooks.pretool.phases.step_gate._HAS_LIFE_DB", True)


@pytest.fixture(autouse=True)
def _enable_life_db():
    with _LIFE_DB_PATCH:
        yield


@pytest.fixture
def skill_dir(tmp_path):
    """Create a skill with step files that have consumes/produces frontmatter."""
    skill = tmp_path / "skills" / "test-skill" / "steps"
    skill.mkdir(parents=True)

    # Step 1: root step (consumes user-request only)
    (skill / "clarification.md").write_text(
        "---\nconsumes: [user-request]\nproduces: [hunt-target]\n---\n# Clarification\n"
    )
    # Step 2: depends on clarification
    (skill / "topology.md").write_text(
        "---\nconsumes: [hunt-target]\nproduces: [code-topology]\n---\n# Topology\n"
    )
    # Step 3: depends on both
    (skill / "hunt.md").write_text(
        "---\nconsumes: [hunt-target, code-topology]\nproduces: [hunt-findings]\n---\n# Hunt\n"
    )
    # Step 4: depends on hunt
    (skill / "synthesis.md").write_text(
        "---\nconsumes: [hunt-findings]\nproduces: [report]\n---\n# Synthesis\n"
    )
    return tmp_path


def _make_ctx(file_path: str) -> dict:
    return {"tool_name": "Read", "tool_input": {"file_path": file_path}}


class TestRootStepAlwaysAllowed:
    """Steps that only consume user-request should always pass."""

    def test_root_step_allowed_with_no_span(self, skill_dir):
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        path = str(skill_dir / "skills" / "test-skill" / "steps" / "clarification.md")
        ctx = _make_ctx(path)

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", skill_dir / "skills"):
            result = sg.check(ctx)

        assert result is None  # allowed


class TestDependencySatisfied:
    """Steps whose dependencies have been visited should pass."""

    def test_step_allowed_when_producer_visited(self, skill_dir):
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        path = str(skill_dir / "skills" / "test-skill" / "steps" / "topology.md")
        ctx = _make_ctx(path)

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = ["clarification"]
            result = sg.check(ctx)

        assert result is None  # allowed


class TestDependencyBlocked:
    """Steps whose dependencies haven't been visited should block."""

    def test_step_blocked_when_producer_not_visited(self, skill_dir):
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        path = str(skill_dir / "skills" / "test-skill" / "steps" / "topology.md")
        ctx = _make_ctx(path)

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = []
            result = sg.check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "clarification" in result["reason"]

    def test_step_blocked_when_partial_deps(self, skill_dir):
        """hunt needs hunt-target AND code-topology. Only clarification visited."""
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        path = str(skill_dir / "skills" / "test-skill" / "steps" / "hunt.md")
        ctx = _make_ctx(path)

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = ["clarification"]
            result = sg.check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "topology" in result["reason"]

    def test_deep_chain_blocked(self, skill_dir):
        """synthesis needs hunt-findings (from hunt). Only clarification visited."""
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        path = str(skill_dir / "skills" / "test-skill" / "steps" / "synthesis.md")
        ctx = _make_ctx(path)

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = ["clarification", "topology"]
            result = sg.check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "hunt" in result["reason"]


class TestNonStepReadsIgnored:
    """Non-step-file reads should pass through."""

    def test_non_read_tool_ignored(self):
        from hooks.pretool.phases.step_gate import check
        result = check({"tool_name": "Write", "tool_input": {"file_path": "/foo"}})
        assert result is None

    def test_non_step_file_ignored(self):
        from hooks.pretool.phases.step_gate import check
        ctx = _make_ctx("/Users/me/.claude/skills/test-skill/SKILL.md")
        result = check(ctx)
        assert result is None

    def test_internal_skill_ignored(self):
        """Skills starting with _ (like _partials) should be ignored."""
        from hooks.pretool.phases.step_gate import check
        ctx = _make_ctx("/Users/me/.claude/skills/_partials/steps/foo.md")
        result = check(ctx)
        assert result is None


class TestNoFrontmatter:
    """Steps without frontmatter should be allowed (graceful degradation)."""

    def test_step_without_frontmatter_allowed(self, tmp_path):
        skill = tmp_path / "skills" / "old-skill" / "steps"
        skill.mkdir(parents=True)
        (skill / "do-stuff.md").write_text("# Just do stuff\nNo frontmatter here.\n")

        ctx = _make_ctx(str(skill / "do-stuff.md"))

        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", tmp_path / "skills"):
            result = sg.check(ctx)

        assert result is None


@pytest.fixture
def optional_skill_dir(tmp_path):
    """Create a skill with an optional step in the dependency chain."""
    skill = tmp_path / "skills" / "modal-skill" / "steps"
    skill.mkdir(parents=True)

    (skill / "gather.md").write_text(
        "---\nconsumes: [user-request]\nproduces: [raw-data]\n---\n# Gather\n"
    )
    # Optional step — skipped in quick mode
    (skill / "verify.md").write_text(
        "---\nconsumes: [raw-data]\nproduces: [verified-data]\noptional: true\n---\n# Verify\n"
    )
    # Consumes artifact from optional step
    (skill / "report.md").write_text(
        "---\nconsumes: [verified-data, raw-data]\nproduces: [final-report]\n---\n# Report\n"
    )
    return tmp_path


class TestOptionalProducer:
    """Optional steps that are skipped should not block downstream consumers."""

    def test_optional_producer_allows_through(self, optional_skill_dir):
        """When optional step 'verify' is skipped, 'report' should still be allowed."""
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()
        sg._optional_steps.clear()

        path = str(optional_skill_dir / "skills" / "modal-skill" / "steps" / "report.md")
        ctx = _make_ctx(path)

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", optional_skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = ["gather"]
            result = sg.check(ctx)

        assert result is None  # allowed — verify is optional

    def test_optional_producer_still_allows_when_visited(self, optional_skill_dir):
        """When optional step IS visited, downstream should still work (no regression)."""
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()
        sg._optional_steps.clear()

        path = str(optional_skill_dir / "skills" / "modal-skill" / "steps" / "report.md")
        ctx = _make_ctx(path)

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", optional_skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = ["gather", "verify"]
            result = sg.check(ctx)

        assert result is None  # allowed

    def test_non_optional_still_blocks(self, optional_skill_dir):
        """Non-optional producer 'gather' not visited — should still block."""
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()
        sg._optional_steps.clear()

        path = str(optional_skill_dir / "skills" / "modal-skill" / "steps" / "report.md")
        ctx = _make_ctx(path)

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", optional_skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = []
            result = sg.check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "gather" in result["reason"]


class TestCaching:
    """Contract maps should be cached per skill."""

    def test_contracts_cached_after_first_build(self, skill_dir):
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", skill_dir / "skills"):
            sg._build_contracts("test-skill")

        assert "test-skill" in sg._produces_map
        assert "hunt-target" in sg._produces_map["test-skill"]
        assert sg._produces_map["test-skill"]["hunt-target"] == "clarification"

        assert sg._consumes_map["test-skill"]["topology"] == ["hunt-target"]
        assert sg._consumes_map["test-skill"]["hunt"] == ["hunt-target", "code-topology"]

    def test_optional_steps_cached(self, optional_skill_dir):
        """_optional_steps should be populated after _build_contracts()."""
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()
        sg._optional_steps.clear()

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", optional_skill_dir / "skills"):
            sg._build_contracts("modal-skill")

        assert "modal-skill" in sg._optional_steps
        assert "verify" in sg._optional_steps["modal-skill"]
        assert "gather" not in sg._optional_steps["modal-skill"]


class TestDBOnlyGate:
    """Tests for _get_span_steps querying DB directly (no stack file)."""

    def test_get_span_steps_returns_visited_from_db(self):
        """Active span with steps returns those steps."""
        import hooks.pretool.phases.step_gate as sg

        mock_db = MagicMock()
        mock_row = {"steps": json.dumps(["clarification", "topology"])}
        mock_db.execute.return_value.fetchone.return_value = mock_row

        with patch("hooks.pretool.phases.step_gate.get_db", return_value=mock_db):
            result = sg._get_span_steps("test-skill")

        assert result == ["clarification", "topology"]
        # Verify correct SQL
        call_args = mock_db.execute.call_args
        assert "skill = ?" in call_args[0][0]
        assert "status = 'active'" in call_args[0][0]
        assert call_args[0][1] == ("test-skill",)
        mock_db.close.assert_called_once()

    def test_get_span_steps_returns_empty_on_no_active_span(self):
        """No active span returns empty list."""
        import hooks.pretool.phases.step_gate as sg

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None

        with patch("hooks.pretool.phases.step_gate.get_db", return_value=mock_db):
            result = sg._get_span_steps("test-skill")

        assert result == []

    def test_get_span_steps_returns_empty_on_db_error(self):
        """DB error returns empty list (fail-open)."""
        import hooks.pretool.phases.step_gate as sg

        with patch("hooks.pretool.phases.step_gate.get_db", side_effect=Exception("DB locked")):
            result = sg._get_span_steps("nonexistent-skill")

        assert result == []

    def test_get_span_steps_picks_latest_span(self):
        """ORDER BY started_at DESC LIMIT 1 picks the most recent span."""
        import hooks.pretool.phases.step_gate as sg

        mock_db = MagicMock()
        mock_row = {"steps": json.dumps(["step-a"])}
        mock_db.execute.return_value.fetchone.return_value = mock_row

        with patch("hooks.pretool.phases.step_gate.get_db", return_value=mock_db):
            sg._get_span_steps("test-skill")

        sql = mock_db.execute.call_args[0][0]
        assert "ORDER BY started_at DESC LIMIT 1" in sql

    def test_get_span_steps_handles_empty_steps_field(self):
        """Span with empty/null steps field returns empty list."""
        import hooks.pretool.phases.step_gate as sg

        mock_db = MagicMock()
        mock_row = {"steps": None}
        mock_db.execute.return_value.fetchone.return_value = mock_row

        with patch("hooks.pretool.phases.step_gate.get_db", return_value=mock_db):
            result = sg._get_span_steps("test-skill")

        assert result == []


class TestSessionIsolation:
    """Step gate must scope span queries by session_id."""

    def test_get_span_steps_filters_by_session_id(self):
        """_get_span_steps query must include session_id filter."""
        import hooks.pretool.phases.step_gate as sg

        mock_db = MagicMock()
        mock_row = {"steps": json.dumps(["step-a"])}
        mock_db.execute.return_value.fetchone.return_value = mock_row

        with patch("hooks.pretool.phases.step_gate.get_db", return_value=mock_db):
            sg._get_span_steps("test-skill", session_id="session-A")

        sql = mock_db.execute.call_args[0][0]
        params = mock_db.execute.call_args[0][1]
        assert "session_id = ?" in sql
        assert "session-A" in params

    def test_check_passes_session_id_to_get_span_steps(self, skill_dir):
        """check() must extract session_id from ctx and pass to _get_span_steps."""
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        path = str(skill_dir / "skills" / "test-skill" / "steps" / "topology.md")
        ctx = _make_ctx(path)
        ctx["session_id"] = "session-123"

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = ["clarification"]
            sg.check(ctx)

        mock_steps.assert_called_once_with("test-skill", session_id="session-123")

    def test_no_session_id_still_works(self, skill_dir):
        """When session_id is missing from ctx, gate still functions (backcompat)."""
        import hooks.pretool.phases.step_gate as sg
        sg._produces_map.clear()
        sg._consumes_map.clear()

        path = str(skill_dir / "skills" / "test-skill" / "steps" / "topology.md")
        ctx = _make_ctx(path)
        # No session_id in ctx

        with patch("hooks.pretool.phases.step_gate._SKILLS_DIR", skill_dir / "skills"), \
             patch("hooks.pretool.phases.step_gate._get_span_steps") as mock_steps:
            mock_steps.return_value = ["clarification"]
            sg.check(ctx)

        mock_steps.assert_called_once_with("test-skill", session_id=None)
