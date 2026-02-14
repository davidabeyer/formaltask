"""Tests verifying stale reviews block completion after code changes (Task #2925).

Acceptance criteria:
- Completion blocked after post-review code change with stale_reviews reason
- Fresh review after latest code change unblocks completion
"""

import subprocess


class TestStaleReviewsBlockCompletion:
    """Verify _get_stale_reviews detects when review SHA != HEAD SHA."""

    def test_review_at_old_sha_is_stale_when_code_changed(self, db_path, monkeypatch):
        """Review done at SHA-A becomes stale when HEAD moves to SHA-B with code changes."""
        from formaltask.core.completion_state import _get_stale_reviews
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import utils as git_utils

        old_sha = "a" * 40
        new_sha = "b" * 40

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at, reviewed_sha)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z', ?)""",
                (old_sha,),
            )
            cursor = conn.cursor()

            monkeypatch.setattr(git_utils, "get_head_sha", lambda: new_sha)

            monkeypatch.setattr(
                "formaltask.core.completion_state.subprocess.run",
                lambda *a, **_kw: subprocess.CompletedProcess(
                    args=a[0], returncode=0, stdout="src/main.py\n", stderr=""
                ),
            )

            stale = _get_stale_reviews(1, cursor, {"code-quality"})

        assert "code-quality" in stale

    def test_review_at_head_sha_is_fresh(self, db_path, monkeypatch):
        """Review done at same SHA as HEAD is not stale."""
        from formaltask.core.completion_state import _get_stale_reviews
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import utils as git_utils

        current_sha = "c" * 40

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at, reviewed_sha)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z', ?)""",
                (current_sha,),
            )
            cursor = conn.cursor()

            monkeypatch.setattr(git_utils, "get_head_sha", lambda: current_sha)

            stale = _get_stale_reviews(1, cursor, {"code-quality"})

        assert stale == set()


class TestStaleReviewsCompletionCheck:
    """Verify stale reviews rule blocks/unblocks completion via check_completion."""

    def test_completion_blocked_when_review_stale(self, db_path, monkeypatch):
        """check_completion blocks when review SHA != HEAD SHA (AC-1)."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import utils as git_utils

        old_sha = "a" * 40
        new_sha = "b" * 40

        monkeypatch.setattr(completion_rules, "REQUIRED_REVIEWS", ["code-quality"])
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", True)
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
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at, reviewed_sha)
                   VALUES (1, 'code-quality', 'clean', '{"findings": [], "summary": "ok"}', 1, '2025-01-01T00:00:00Z', ?)""",
                (old_sha,),
            )

        monkeypatch.setattr(git_utils, "get_head_sha", lambda: new_sha)

        monkeypatch.setattr(
            "formaltask.core.completion_state.subprocess.run",
            lambda *a, **_kw: subprocess.CompletedProcess(
                args=a[0], returncode=0, stdout="src/main.py\n", stderr=""
            ),
        )

        result = check_completion(1, db_path)

        assert result is not None
        assert result.allowed is False
        assert "Stale reviews" in (result.reason or "")
        assert "code-quality" in (result.reason or "")

    def test_completion_allowed_after_fresh_review(self, db_path, monkeypatch):
        """check_completion allows when fresh review covers HEAD SHA (AC-2)."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import utils as git_utils

        current_sha = "c" * 40

        monkeypatch.setattr(completion_rules, "REQUIRED_REVIEWS", ["code-quality"])
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", True)
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
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at, reviewed_sha)
                   VALUES (1, 'code-quality', 'clean', '{"findings": [], "summary": "ok"}', 1, '2025-01-01T00:00:00Z', ?)""",
                (current_sha,),
            )

        monkeypatch.setattr(git_utils, "get_head_sha", lambda: current_sha)

        result = check_completion(1, db_path)

        assert result is not None
        # Should not be blocked by stale reviews (may be blocked for other reasons like PR)
        assert "Stale reviews" not in (result.reason or "")
