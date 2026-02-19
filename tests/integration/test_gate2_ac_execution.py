"""Integration tests for Gate 2 AC execution (Task #2872).

Verifies ft task-complete correctly executes AC commands and blocks on failure.
Tests both passing (exit 0) and failing (exit 1) scenarios.
"""

from tests.conftest import make_valid_review_findings


def _setup_task_with_reviews(conn, ac_command: str) -> None:
    """Helper to create test task with required reviews (passes earlier rules)."""
    conn.execute(
        "INSERT INTO epics (name, description, created_at) VALUES "
        "('test-epic', 'Test epic', '2025-01-01T00:00:00Z')"
    )
    conn.execute(
        """INSERT INTO tasks (title, epic_name, description, status, created_at)
           VALUES ('Test task', 'test-epic', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
    )
    # Add AC with command
    conn.execute(
        f"""INSERT INTO acceptance_criteria (task_id, text, command)
           VALUES (1, 'AC test', '{ac_command}')"""
    )
    # Add required review (so has_reviews=True)
    findings = make_valid_review_findings()
    conn.execute(
        f"""INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
           VALUES (1, 'acceptance', 'clean', '{findings}', 1, '2025-01-01T00:00:00Z')"""
    )


class TestGate2PassingAC:
    """Test Gate 2 allows completion when AC command passes."""

    def test_passing_ac_allows_completion(self, db_path, monkeypatch):
        """Task with passing AC (exit 0) should allow completion."""
        from formaltask.core import rules_config
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        # Enable AC checking, disable PR requirement and freshness check
        monkeypatch.setattr(rules_config, "CHECK_AC", True)
        monkeypatch.setattr(rules_config, "REQUIRE_PR_MERGED", False)
        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            _setup_task_with_reviews(conn, "exit 0")

        result = check_completion(1, db_path)

        # Passing AC should allow completion (not blocked by ac_failed)
        assert result is not None
        assert result.allowed is True, f"Expected allowed=True but got {result}"


class TestGate2FailingAC:
    """Test Gate 2 blocks completion when AC command fails."""

    def test_failing_ac_blocks_completion(self, db_path, monkeypatch):
        """Task with failing AC (exit 1) should block completion with ac_failed."""
        from formaltask.core import rules_config
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        # Enable AC checking, disable PR requirement and freshness check
        monkeypatch.setattr(rules_config, "CHECK_AC", True)
        monkeypatch.setattr(rules_config, "REQUIRE_PR_MERGED", False)
        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            _setup_task_with_reviews(conn, "exit 1")

        result = check_completion(1, db_path)

        # Should be blocked
        assert result is not None
        assert result.allowed is False
        assert result.phase == "needs_fix"
        # Reason should mention AC failure
        assert result.reason is not None
        assert "acceptance criteria" in result.reason.lower() or "exit" in result.reason.lower()

    def test_failing_ac_includes_exit_code_in_reason(self, db_path, monkeypatch):
        """Failing AC should include exit code in the reason message."""
        from formaltask.core import rules_config
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        # Enable AC checking, disable PR requirement and freshness check
        monkeypatch.setattr(rules_config, "CHECK_AC", True)
        monkeypatch.setattr(rules_config, "REQUIRE_PR_MERGED", False)
        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            _setup_task_with_reviews(conn, "exit 42")

        result = check_completion(1, db_path)

        assert result is not None
        assert result.allowed is False
        # Reason should contain the exit code
        assert result.reason is not None
        assert "42" in result.reason


class TestGate2MixedAC:
    """Test Gate 2 behavior with mixed AC commands."""

    def test_one_failing_ac_blocks_even_with_passing(self, db_path, monkeypatch):
        """If any AC command fails, completion should be blocked."""
        from formaltask.core import rules_config
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        # Enable AC checking, disable PR requirement and freshness check
        monkeypatch.setattr(rules_config, "CHECK_AC", True)
        monkeypatch.setattr(rules_config, "REQUIRE_PR_MERGED", False)
        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES "
                "('test-epic', 'Test epic', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test-epic', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Add multiple AC - one passing, one failing
            conn.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (1, 'Passing check', 'exit 0')"""
            )
            conn.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (1, 'Failing check', 'exit 1')"""
            )
            # Add required review
            findings = make_valid_review_findings()
            conn.execute(
                f"""INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'acceptance', 'clean', '{findings}', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)

        assert result is not None
        assert result.allowed is False
        assert result.phase == "needs_fix"
