"""Tests for formaltask.core.completion_state module (Task #2734).

Tests the evaluate() condition parser and fetch_completion_state() function.
"""

import json

import pytest


class TestFetchCompletionStateImport:
    """Tests for fetch_completion_state function."""

    def test_returns_dict_for_existing_task(self, db_path):
        """fetch_completion_state returns dict for existing task."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert isinstance(state, dict)

    def test_returns_none_for_nonexistent_task(self, db_path):
        """fetch_completion_state returns None for nonexistent task."""
        from formaltask.core.completion_state import fetch_completion_state

        state = fetch_completion_state(99999, db_path)
        assert state is None


class TestFetchCompletionStateClosedTasks:
    """Test state dict for closed tasks (completed/cancelled)."""

    @pytest.mark.parametrize("status", ["cancelled", "completed"])
    def test_closed_task_returns_closed_state(self, db_path, status):
        """Closed tasks (cancelled/completed) return minimal closed state."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                f"""INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', '{status}', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert state["status"] == status
        assert state["closed"] is True


class TestFetchCompletionStateBlocked:
    """Test blocked status detection."""

    def test_blocked_user_status(self, db_path):
        """blocked_user status sets blocked flag."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'blocked_user', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert state["blocked"] is True


class TestFetchCompletionStateReviews:
    """Test review state gathering."""

    @pytest.mark.parametrize(
        "has_review,expected",
        [
            (False, False),
            (True, True),
        ],
        ids=["no_reviews", "with_reviews"],
    )
    def test_has_reviews_flag(self, db_path, has_review, expected):
        """has_reviews reflects whether task has any reviews."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            if has_review:
                conn.execute(
                    """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                       VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
                )

        state = fetch_completion_state(1, db_path)
        assert state["has_reviews"] is expected

    def test_present_reviews_tracking(self, db_path):
        """present_reviews contains all review types present."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'security', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert state["present_reviews"] == {"code-quality", "security"}


class TestFetchCompletionStateRequiredReviews:
    """Test required_reviews state gathering."""

    def test_uses_default_required_reviews(self, db_path, monkeypatch):
        """Uses REQUIRED_REVIEWS from rules when metadata doesn't specify."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "REQUIRED_REVIEWS", ["code-quality", "security"])

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert state["required_reviews"] == {"code-quality", "security"}

    def test_uses_metadata_required_reviews_when_present(self, db_path, monkeypatch):
        """Uses required_reviews from metadata when specified."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "REQUIRED_REVIEWS", ["code-quality"])

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{"required_reviews": ["code-quality", "migration"]}', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert state["required_reviews"] == {"code-quality", "migration"}


class TestGetBlockingFindings:
    """Test _get_blocking_findings helper (Task #2743)."""

    def test_filters_blocking_priorities(self):
        """_get_blocking_findings returns only P0/P1 priorities."""
        from formaltask.core.completion_state import _get_blocking_findings

        findings = [
            {
                "file": "a.py",
                "line": 1,
                "priority": "P0",
                "description": "critical",
                "disposition": None,
            },
            {
                "file": "b.py",
                "line": 2,
                "priority": "P1",
                "description": "high",
                "disposition": None,
            },
            {
                "file": "c.py",
                "line": 3,
                "priority": "P2",
                "description": "medium",
                "disposition": None,
            },
            {
                "file": "d.py",
                "line": 4,
                "priority": "P3",
                "description": "low",
                "disposition": None,
            },
        ]
        result = _get_blocking_findings(findings)
        assert len(result) == 2
        priorities = {f["priority"] for f in result}
        assert priorities == {"P0", "P1"}

    def test_excludes_resolved_dispositions(self):
        """_get_blocking_findings excludes WONTFIX, FIXED, NEEDSHUMAN dispositions."""
        from formaltask.core.completion_state import _get_blocking_findings

        findings = [
            {
                "file": "a.py",
                "line": 1,
                "priority": "P0",
                "description": "open",
                "disposition": None,
            },
            {
                "file": "b.py",
                "line": 2,
                "priority": "P0",
                "description": "fixed",
                "disposition": "fixed",
            },
            {
                "file": "c.py",
                "line": 3,
                "priority": "P1",
                "description": "wontfix",
                "disposition": "wontfix",
            },
            {
                "file": "d.py",
                "line": 4,
                "priority": "P1",
                "description": "needshuman",
                "disposition": "needshuman",
            },
        ]
        result = _get_blocking_findings(findings)
        assert len(result) == 1
        assert result[0]["file"] == "a.py"


class TestCheckLowFindingsExceeded:
    """Test _check_low_findings_exceeded helper (Task #2743)."""

    def test_counts_low_priority_findings(self, monkeypatch):
        """_check_low_findings_exceeded counts P2/P3 findings against limit."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import _check_low_findings_exceeded

        monkeypatch.setattr(completion_rules, "MAX_LOW_PRIORITY_FINDINGS", 2)

        findings = [
            {
                "file": "a.py",
                "line": 1,
                "priority": "P2",
                "description": "med",
                "disposition": None,
            },
            {
                "file": "b.py",
                "line": 2,
                "priority": "P3",
                "description": "low",
                "disposition": None,
            },
        ]
        assert _check_low_findings_exceeded(findings) is False

        findings.append(
            {
                "file": "c.py",
                "line": 3,
                "priority": "P2",
                "description": "med2",
                "disposition": None,
            }
        )
        assert _check_low_findings_exceeded(findings) is True

    def test_excludes_resolved_dispositions(self, monkeypatch):
        """_check_low_findings_exceeded excludes WONTFIX and FIXED dispositions."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import _check_low_findings_exceeded

        monkeypatch.setattr(completion_rules, "MAX_LOW_PRIORITY_FINDINGS", 1)

        findings = [
            {
                "file": "a.py",
                "line": 1,
                "priority": "P2",
                "description": "open",
                "disposition": None,
            },
            {
                "file": "b.py",
                "line": 2,
                "priority": "P3",
                "description": "fixed",
                "disposition": "fixed",
            },
            {
                "file": "c.py",
                "line": 3,
                "priority": "P2",
                "description": "wontfix",
                "disposition": "wontfix",
            },
        ]
        result = _check_low_findings_exceeded(findings)
        assert result is False  # Only 1 open finding, limit is 1

    def test_returns_false_when_limit_disabled(self, monkeypatch):
        """_check_low_findings_exceeded returns False when MAX_LOW_PRIORITY_FINDINGS is None."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import _check_low_findings_exceeded

        monkeypatch.setattr(completion_rules, "MAX_LOW_PRIORITY_FINDINGS", None)

        findings = [
            {
                "file": "a.py",
                "line": 1,
                "priority": "P2",
                "description": "issue",
                "disposition": None,
            },
            {
                "file": "b.py",
                "line": 2,
                "priority": "P3",
                "description": "issue2",
                "disposition": None,
            },
        ]
        result = _check_low_findings_exceeded(findings)
        assert result is False


class TestHasDocCommits:
    """Test _has_doc_commits helper (Task #2743)."""

    def test_catches_operational_error_for_missing_table(self, db_path):
        """_has_doc_commits catches OperationalError when commit_files table missing."""
        from formaltask.core.completion_state import _has_doc_commits
        from formaltask.db.connection import DatabaseConnection

        # Create cursor but don't create commit_files table
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            # Should return True (fail open) when table doesn't exist
            result = _has_doc_commits(1, cursor)
            assert result is True


class TestFetchCompletionStateReviewRounds:
    """Test review_rounds state gathering."""

    def test_review_rounds_in_state(self, db_path):
        """review_rounds dict has max round per review type."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # 2 rounds of self-critique
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'minor', '[]', 1, '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'clean', '[]', 2, '2025-01-01T00:00:00Z')"""
            )
            # 1 round of code-review
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-review', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert state["review_rounds"] == {"self-critique": 2, "code-review": 1}

    def test_review_rounds_empty_when_no_reviews(self, db_path):
        """review_rounds is empty dict when no reviews exist."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert state["review_rounds"] == {}


class TestFetchCompletionStateCompletionRules:
    """Test completion_rules state gathering."""

    def test_completion_rules_from_metadata(self, db_path):
        """completion_rules populated from metadata when present."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        rules = [{"when": "blocking_findings AND review_rounds.self-critique >= 2", "then": "needs_escalation", "target": "task.phase", "priority": 1, "name": "round cap"}]
        metadata = json.dumps({"completion_rules": rules})

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', ?, '2025-01-01T00:00:00Z')""",
                (metadata,),
            )

        state = fetch_completion_state(1, db_path)
        assert state["completion_rules"] == rules

    def test_completion_rules_empty_by_default(self, db_path):
        """completion_rules is empty list when not in metadata."""
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)
        assert state["completion_rules"] == []


class TestEvaluateConditionParser:
    """Test evaluate() condition evaluation."""

    @pytest.mark.parametrize(
        "state,condition,expected",
        [
            # Simple key evaluation
            ({"blocked": True}, "blocked", True),
            ({"blocked": False}, "blocked", False),
            ({}, "blocked", False),
            # Negation (new DSL: NOT instead of !)
            ({"blocked": False}, "NOT blocked", True),
            ({"blocked": True}, "NOT blocked", False),
            ({}, "NOT blocked", True),
            # AND operator (new DSL: AND instead of &)
            ({"a": True, "b": True}, "a AND b", True),
            ({"a": True, "b": False}, "a AND b", False),
            ({"a": False, "b": False}, "a AND b", False),
            # Equality operator (new DSL: == instead of =)
            ({"status": "cancelled"}, "status == cancelled", True),
            ({"status": "completed"}, "status == cancelled", False),
            ({}, "status == cancelled", False),
            # True literal (new DSL: true instead of *)
            ({}, "true", True),
            ({"a": 1, "b": 2}, "true", True),
        ],
        ids=[
            "simple_true",
            "simple_false",
            "simple_missing",
            "negation_true",
            "negation_false",
            "negation_missing",
            "and_both_true",
            "and_one_false",
            "and_both_false",
            "eq_match",
            "eq_mismatch",
            "eq_missing",
            "wildcard_empty",
            "wildcard_populated",
        ],
    )
    def test_condition_evaluation(self, state, condition, expected):
        """evaluate() evaluates conditions correctly."""
        from formaltask.core.rules import evaluate

        assert evaluate(condition, state) is expected

    def test_complex_condition(self):
        """Complex AND with equality and negation."""
        from formaltask.core.rules import evaluate

        state = {"require_pr_merged": True, "has_pr": False}
        assert evaluate("require_pr_merged AND NOT has_pr", state) is True

        state["has_pr"] = True
        assert evaluate("require_pr_merged AND NOT has_pr", state) is False

    def test_truthy_non_boolean(self):
        """Non-empty collections and non-zero values are truthy."""
        from formaltask.core.rules import evaluate

        assert evaluate("items", {"items": [1, 2, 3]}) is True
        assert evaluate("items", {"items": []}) is False
        assert evaluate("count", {"count": 5}) is True
        assert evaluate("count", {"count": 0}) is False
        assert evaluate("text", {"text": "hello"}) is True
        assert evaluate("text", {"text": ""}) is False

    def test_set_truthy(self):
        """Non-empty set is truthy, empty set is falsy."""
        from formaltask.core.rules import evaluate

        assert evaluate("missing_reviews", {"missing_reviews": {"code-quality"}}) is True
        assert evaluate("missing_reviews", {"missing_reviews": set()}) is False


class TestFetchCompletionStateUsesConfig:
    """Test fetch_completion_state uses get_effective_config (Task #2821)."""

    def test_uses_config_for_check_docs(self, db_path, monkeypatch):
        """fetch_completion_state uses config.check_docs from get_effective_config."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        # Set CHECK_DOCS to False via rules (get_effective_config reads this)
        monkeypatch.setattr(completion_rules, "CHECK_DOCS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            # Task with documentation_required=True in metadata
            metadata = json.dumps({"documentation_required": True})
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', ?, '2025-01-01T00:00:00Z')""",
                (metadata,),
            )

        state = fetch_completion_state(1, db_path)

        # Even though documentation_required is True, check_docs is False so it shouldn't check
        assert state["check_docs"] is False

    def test_uses_config_for_check_learnings(self, db_path, monkeypatch):
        """fetch_completion_state uses config.check_learnings from get_effective_config."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_LEARNINGS", True)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)

        assert state["check_learnings"] is True

    def test_uses_config_for_require_pr(self, db_path, monkeypatch):
        """fetch_completion_state uses config.require_pr from get_effective_config."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "REQUIRE_PR", True)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, db_path)

        assert state["require_pr"] is True


class TestFetchCompletionStateAcExecution:
    """Test AC command execution in fetch_completion_state (Task #2860)."""

    def test_includes_ac_results_when_check_ac_enabled(self, db_path, monkeypatch):
        """fetch_completion_state includes ac_results when check_ac config is enabled."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_AC", True)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Add acceptance criterion with passing command
            conn.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (1, 'test criterion', 'exit 0')"""
            )

        state = fetch_completion_state(1, db_path)

        assert "ac_results" in state
        assert "ac_failed" in state
        assert state["ac_results"]["passed"] == ["test criterion"]
        assert state["ac_results"]["failed"] == []
        assert state["ac_failed"] is False

    def test_ac_failed_true_when_command_fails(self, db_path, monkeypatch):
        """fetch_completion_state sets ac_failed=True when AC command fails."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_AC", True)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Add acceptance criterion with failing command
            conn.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (1, 'test criterion', 'exit 1')"""
            )

        state = fetch_completion_state(1, db_path)

        assert state["ac_failed"] is True
        assert len(state["ac_results"]["failed"]) == 1

    def test_ac_failed_reason_formatted_with_output(self, db_path, monkeypatch):
        """fetch_completion_state sets ac_failed_reason with command output."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_AC", True)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (1, 'test criterion', 'exit 1')"""
            )

        state = fetch_completion_state(1, db_path)

        assert "ac_failed_reason" in state
        assert "test criterion" in state["ac_failed_reason"]

    def test_skips_ac_check_when_disabled(self, db_path, monkeypatch):
        """fetch_completion_state skips AC execution when check_ac is disabled."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_state import fetch_completion_state
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_AC", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (1, 'test criterion', 'exit 1')"""
            )

        state = fetch_completion_state(1, db_path)

        # AC execution should be skipped
        assert state.get("check_ac") is False
        assert state.get("ac_failed") is False


class TestAcFailedCompletionRule:
    """Test AC failed rule in completion check (Task #2860)."""

    def test_ac_failed_rule_blocks_completion(self, db_path, monkeypatch):
        """check_ac&ac_failed condition blocks completion with ac_failed_reason."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_AC", True)
        monkeypatch.setattr(completion_rules, "REQUIRED_REVIEWS", [])
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (1, 'test criterion', 'exit 1')"""
            )
            # Add a review to get past the "no reviews" rule
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '{"findings": [], "summary": "ok"}', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)

        assert result.allowed is False
        assert "Acceptance criteria" in (result.reason or "")

    def test_evaluate_check_ac_and_ac_failed(self):
        """evaluate() evaluates check_ac AND ac_failed condition correctly."""
        from formaltask.core.rules import evaluate

        # Both check_ac and ac_failed true = match
        state = {"check_ac": True, "ac_failed": True}
        assert evaluate("check_ac AND ac_failed", state) is True

        # check_ac true but ac_failed false = no match
        state = {"check_ac": True, "ac_failed": False}
        assert evaluate("check_ac AND ac_failed", state) is False

        # check_ac false = no match regardless of ac_failed
        state = {"check_ac": False, "ac_failed": True}
        assert evaluate("check_ac AND ac_failed", state) is False

    def test_passing_ac_commands_allows_completion(self, db_path, monkeypatch):
        """Passing AC commands do not block completion (AC c-4)."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_AC", True)
        monkeypatch.setattr(completion_rules, "REQUIRED_REVIEWS", [])
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)
        # Disable PR requirement
        monkeypatch.setattr(completion_rules, "REQUIRE_PR", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR_MERGED", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Add acceptance criterion with PASSING command
            conn.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (1, 'test criterion', 'exit 0')"""
            )
            # Add a review
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '{"findings": [], "summary": "ok"}', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)

        # Should NOT block completion since AC command passes
        assert result is not None
        # Reason should NOT be about AC failure
        if result.reason:
            assert "Acceptance criteria" not in result.reason


