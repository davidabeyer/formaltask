"""Tests for formaltask.core.completion_check module (Task #2614).

Tests the unified completion checking logic that replaces check_review_gates_v2()
and derive_worker_phase().
"""


class TestCheckCompletionBasicBehavior:
    """Test basic check_completion behavior."""

    def test_returns_completion_check_instance(self, db_path):
        """check_completion returns a CompletionCheck instance."""
        from formaltask.core.completion_check import CompletionCheck, check_completion
        from formaltask.db.connection import DatabaseConnection

        # Create a minimal task
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert isinstance(result, CompletionCheck)

    def test_nonexistent_task_returns_none(self, db_path):
        """check_completion returns None for nonexistent task."""
        from formaltask.core.completion_check import check_completion

        result = check_completion(99999, db_path)
        assert result is None

    def test_completed_task_returns_done_phase(self, db_path):
        """Completed task returns phase='done'."""
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'completed', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.phase == "done"


class TestBlockPrioritiesEnvVar:
    """Test BLOCK_PRIORITIES configuration behavior."""

    def test_p0_p1_p2_blocks_p2_findings(self, db_path, monkeypatch):
        """BLOCK_PRIORITIES={P0,P1,P2} makes P2 findings block."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "BLOCK_PRIORITIES", frozenset({"P0", "P1", "P2"}))

        # Create task with P2 finding
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Add a P2 finding via task_reviews
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'minor',
                   '[{"priority": "P2", "file": "test.py", "line": 1, "description": "test"}]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.allowed is False
        assert "P2" in result.reason or "finding" in result.reason.lower()

    def test_p0_only_allows_p2_findings(self, db_path, monkeypatch):
        """BLOCK_PRIORITIES={P0} makes only P0 block (P2 allowed)."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "BLOCK_PRIORITIES", frozenset({"P0"}))
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)
        # Create task with P2 finding (should be allowed)
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Add a P2 finding - should NOT block with P0-only blocking
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean',
                   '[{"priority": "P2", "file": "test.py", "line": 1, "description": "test"}]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # P2 should not block when only P0 is in BLOCK_PRIORITIES
        # Phase should NOT be needs_fix (P2 findings are non-blocking)
        assert result is not None
        assert result.phase != "needs_fix", f"P2 should not block: got phase={result.phase}"

    def test_p0_blocks_p0_findings(self, db_path, monkeypatch):
        """BLOCK_PRIORITIES={P0} still blocks P0 findings."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "BLOCK_PRIORITIES", frozenset({"P0"}))

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
                   VALUES (1, 'code-quality', 'critical',
                   '[{"priority": "P0", "file": "test.py", "line": 1, "description": "critical bug"}]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.allowed is False


class TestMaxLowFindingsEnvVar:
    """Test MAX_LOW_PRIORITY_FINDINGS configuration behavior."""

    def test_exceeding_max_low_findings_blocks(self, db_path, monkeypatch):
        """MAX_LOW_PRIORITY_FINDINGS=3 blocks if >3 non-blocking findings."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "MAX_LOW_PRIORITY_FINDINGS", 3)
        monkeypatch.setattr(completion_rules, "BLOCK_PRIORITIES", frozenset({"P0", "P1"}))

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Add 4 P2 findings (exceeds limit of 3)
            findings = [
                {"priority": "P2", "file": f"test{i}.py", "line": i, "description": f"issue {i}"}
                for i in range(4)
            ]
            import json

            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', ?, 1, '2025-01-01T00:00:00Z')""",
                (json.dumps(findings),),
            )

        result = check_completion(1, db_path)
        assert result.allowed is False


class TestRequirePREnvVar:
    """Test REQUIRE_PR configuration behavior."""

    def test_require_pr_true_blocks_without_pr(self, db_path, monkeypatch, mock_gh_cli):
        """REQUIRE_PR=True blocks until PR exists."""
        import subprocess

        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import github as github_pr_utils

        monkeypatch.setattr(completion_rules, "REQUIRE_PR", True)
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        # Clear PR cache and mock empty PR list
        github_pr_utils._pr_cache = None
        mock_gh_cli.return_value = subprocess.CompletedProcess(
            args=["gh", "pr", "list"], returncode=0, stdout="[]", stderr=""
        )

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Clean review (no findings)
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'acceptance', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.allowed is False
        assert result.phase == "needs_pr"


class TestRequirePRMergedEnvVar:
    """Test REQUIRE_PR_MERGED configuration behavior."""

    def test_require_pr_merged_true_blocks_unmerged_pr(self, db_path, monkeypatch, mock_gh_cli):
        """REQUIRE_PR_MERGED=True blocks until PR is merged."""
        import json
        import subprocess

        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import github as github_pr_utils

        monkeypatch.setattr(completion_rules, "REQUIRE_PR_MERGED", True)
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        # Clear PR cache and mock PR exists but not merged
        github_pr_utils._pr_cache = None
        pr_data = [{"number": 123, "headRefName": "task-1", "state": "OPEN", "mergedAt": None}]
        mock_gh_cli.return_value = subprocess.CompletedProcess(
            args=["gh", "pr", "list"], returncode=0, stdout=json.dumps(pr_data), stderr=""
        )

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
                   VALUES (1, 'acceptance', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.allowed is False
        assert result.phase == "awaiting_merge"


class TestCheckFreshnessEnvVar:
    """Test CHECK_FRESHNESS configuration behavior."""

    def test_check_freshness_false_disables_freshness_check(self, db_path, monkeypatch):
        """CHECK_FRESHNESS=False disables review freshness check."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Review with old SHA (would fail freshness check normally)
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_sha, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, 'old_sha_that_is_stale', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Should not fail due to freshness when CHECK_FRESHNESS=false
        # Phase should proceed past freshness check (not needs_fix with stale reason)
        assert result is not None
        assert "stale" not in (result.reason or "").lower(), (
            f"Freshness check should be disabled: {result.reason}"
        )


class TestCheckDocsEnvVar:
    """Test CHECK_DOCS configuration behavior."""

    def test_check_docs_false_disables_doc_check(self, db_path, monkeypatch):
        """CHECK_DOCS=False disables documentation_required check."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_DOCS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            # Task with documentation_required=true but no doc files
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{"documentation_required": true}', '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Should not fail due to docs when CHECK_DOCS=false
        # Reason should not mention documentation_required
        assert result is not None
        assert "documentation" not in (result.reason or "").lower(), (
            f"Doc check should be disabled: {result.reason}"
        )


class TestCheckLearningsEnvVar:
    """Test CHECK_LEARNINGS configuration behavior."""

    def test_check_learnings_true_blocks_without_learnings(self, db_path, monkeypatch):
        """CHECK_LEARNINGS=True blocks when no learnings captured."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_LEARNINGS", True)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            # Task without learnings in metadata
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{}', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result is not None
        assert result.allowed is False
        assert result.phase == "needs_reflection"
        assert "/reflect" in result.reason.lower()

    def test_check_learnings_true_allows_with_learnings(self, db_path, monkeypatch):
        """CHECK_LEARNINGS=True allows completion when learnings exist."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_LEARNINGS", True)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            # Task with learnings in metadata
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{"learnings": [{"text": "learned something", "targets": []}]}', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Should not fail due to learnings check
        assert result is not None
        assert "reflection" not in (result.reason or "").lower(), (
            f"Learnings check should pass when learnings exist: {result.reason}"
        )

    def test_check_learnings_false_allows_without_learnings(self, db_path, monkeypatch):
        """CHECK_LEARNINGS=False (default) allows completion without learnings."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_LEARNINGS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            # Task without learnings
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{}', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Should not mention reflection when CHECK_LEARNINGS=false
        assert result is not None
        assert "reflection" not in (result.reason or "").lower(), (
            f"Learnings check should be disabled: {result.reason}"
        )


class TestPhaseDerivation:
    """Test phase derivation logic in check_completion."""

    def test_implementing_phase_for_no_reviews(self, db_path):
        """Task with no reviews returns implementing phase."""
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.phase == "implementing"
        assert result.allowed is False

    def test_needs_fix_phase_for_blocking_findings(self, db_path):
        """Task with blocking findings returns needs_fix phase."""
        from formaltask.core.completion_check import check_completion
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
                   VALUES (1, 'code-quality', 'major',
                   '[{"priority": "P1", "file": "test.py", "line": 1, "description": "bug"}]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.phase == "needs_fix"
        assert result.allowed is False

    def test_cancelled_task_returns_done(self, db_path):
        """Cancelled task returns done phase and allowed=True."""
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'cancelled', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.phase == "done"
        assert result.allowed is True

    def test_needs_human_phase_for_critical_needshuman(self, db_path):
        """Task with P0/P1 finding marked needshuman returns needs_human phase.

        NEEDSHUMAN disposition is excluded from blocking_findings (line 119 of
        completion_check.py), allowing the needs_human phase to be reached.
        """
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # P1 finding
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'major',
                   '[{"priority": "P1", "file": "test.py", "line": 10, "description": "needs human review"}]', 1, '2025-01-01T00:00:00Z')"""
            )
            # Mark it as needshuman disposition
            conn.execute(
                """INSERT INTO finding_dispositions (task_id, file, line, disposition, reason)
                   VALUES (1, 'test.py', 10, 'needshuman', 'Requires human decision')"""
            )

        result = check_completion(1, db_path)
        assert result.phase == "needs_human"
        assert result.allowed is False
        assert "needshuman" in result.reason.lower()

    def test_blocked_user_phase(self, db_path):
        """Task with status=blocked_user returns blocked phase."""
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'blocked_user', '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.phase == "blocked"
        assert result.allowed is False
        assert "blocked" in result.reason.lower()

    def test_doc_check_enabled_blocks_without_docs(self, db_path, monkeypatch):
        """documentation_required=true blocks when CHECK_DOCS=True and no doc files."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_DOCS", True)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            # Task with documentation_required=true
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{"documentation_required": true}', '2025-01-01T00:00:00Z')"""
            )
            # Add commit (no doc files) - uses commit_hash column per schema
            conn.execute(
                """INSERT INTO commits (task_id, commit_hash, commit_message)
                   VALUES (1, 'abc123def456', 'Add feature')"""  # pragma: allowlist secret
            )
            # Add commit_files table for the doc check
            conn.execute(
                """CREATE TABLE IF NOT EXISTS commit_files (
                    commit_sha TEXT,
                    file_path TEXT,
                    PRIMARY KEY (commit_sha, file_path)
                )"""
            )
            # Add a non-doc file
            conn.execute(
                """INSERT INTO commit_files (commit_sha, file_path)
                   VALUES ('abc123def456', 'src/feature.py')"""  # pragma: allowlist secret
            )

        result = check_completion(1, db_path)
        assert result.allowed is False
        assert result.phase == "needs_fix"
        assert "documentation" in result.reason.lower()


class TestRequiredReviewsCheck:
    """Test required_reviews checking (Task #2619)."""

    def test_missing_required_review_blocks_when_freshness_disabled(self, db_path, monkeypatch):
        """Missing required review blocks even when CHECK_FRESHNESS=false.

        Bug: When CHECK_FRESHNESS=false, _check_review_freshness() is skipped.
        That function was the only one catching missing required reviews
        (via _is_fresh returning False when reviewed_sha is None).

        Fix: Add explicit _check_required_reviews() that runs unconditionally.
        """
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        # Disable freshness check - this is where the bug manifests
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            # Task with required_reviews = ["code-quality"]
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{"required_reviews": ["code-quality"]}', '2025-01-01T00:00:00Z')"""
            )
            # Add a DIFFERENT review type - so has_reviews=True but required is missing
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'security', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Should block due to missing required review
        assert result.allowed is False
        assert result.phase == "implementing"
        assert "missing" in result.reason.lower()
        assert "code-quality" in result.reason.lower()

    def test_present_required_review_passes(self, db_path, monkeypatch):
        """Task with required review present passes the check."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{"required_reviews": ["code-quality"]}', '2025-01-01T00:00:00Z')"""
            )
            # Add the REQUIRED review type
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Should NOT block due to missing reviews - required review is present
        assert result is not None
        # Phase should proceed past required reviews check (not stuck in "implementing")
        assert (
            result.phase != "implementing"
            or "missing required reviews" not in (result.reason or "").lower()
        )

    def test_multiple_required_reviews_all_missing(self, db_path, monkeypatch):
        """Task with multiple required reviews all missing."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress',
                   '{"required_reviews": ["code-quality", "security"]}', '2025-01-01T00:00:00Z')"""
            )
            # Add some OTHER review type to pass has_reviews check
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'docs', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.allowed is False
        assert "missing" in result.reason.lower()
        # Should mention BOTH missing reviews
        assert "code-quality" in result.reason.lower() and "security" in result.reason.lower()

    def test_uses_default_required_reviews_when_not_in_metadata(self, db_path, monkeypatch):
        """Uses REQUIRED_REVIEWS default when metadata doesn't specify."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)
        # Default is ["code-quality"] per rules_config.py

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            # No required_reviews in metadata - should use default
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Add a DIFFERENT review type
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'security', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Should block because default "code-quality" is missing
        assert result.allowed is False
        assert "missing" in result.reason.lower()


class TestCleanReviewAllowsCompletion:
    """Test that clean review with all gates passed allows completion."""

    def test_clean_review_all_gates_passed_allows_completion(
        self, db_path, monkeypatch, mock_gh_cli
    ):
        """Clean review with all gates passed returns allowed=True.

        Task #2688: Verifies that when a task has a clean review (no findings),
        passes all required review checks, and doesn't have PR requirements
        blocking it, the completion check returns allowed=True.
        """
        import subprocess

        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import github as github_pr_utils

        # Disable gates that would block completion
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR_MERGED", False)
        monkeypatch.setattr(completion_rules, "CHECK_DOCS", False)

        # Clear PR cache and mock no PR (allowed when REQUIRE_PR=False)
        github_pr_utils._pr_cache = None
        mock_gh_cli.return_value = subprocess.CompletedProcess(
            args=["gh", "pr", "list"], returncode=0, stdout="[]", stderr=""
        )

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Clean review with no findings - all gates pass
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'acceptance', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result is not None
        assert result.allowed is True, f"Expected allowed=True, got {result}"
        assert result.reason is None


class TestTaskLevelCompletionRules:
    """Test task-level completion_rules evaluated before builtins."""

    def test_task_rules_evaluated_before_builtins(self, db_path, monkeypatch):
        """Task-level completion_rules fire before BUILTIN_RULES via check_completion."""
        import json

        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        rules = [
            {
                "when": "blocking_findings AND review_rounds.self-critique >= 2",
                "then": "needs_escalation",
                "target": "task.phase",
                "priority": 1,
                "name": "Round cap reached",
            }
        ]
        metadata = json.dumps(
            {
                "required_reviews": ["self-critique"],
                "completion_rules": rules,
            }
        )

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', ?, '2025-01-01T00:00:00Z')""",
                (metadata,),
            )
            # 2 rounds of self-critique with P1 finding
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug"}]', 1, '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug still there"}]', 2, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Task rule should fire: needs_escalation, not builtin needs_fix
        assert result.phase == "needs_escalation"
        assert result.allowed is False

    def test_task_rules_empty_by_default(self, db_path, monkeypatch):
        """Tasks without completion_rules behave identically to before."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # Review with P1 finding
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug"}]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Should hit builtin blocking_findings rule → needs_fix
        assert result.phase == "needs_fix"
        assert result.allowed is False


class TestDispositionExemptions:
    """Test that WONTFIX and FIXED dispositions exempt findings from blocking."""

    def test_p0_finding_with_wontfix_disposition_does_not_block(
        self, db_path, monkeypatch, mock_gh_cli
    ):
        """P0 finding with WONTFIX disposition does not block completion.

        Task #2688: When a P0 finding is marked with WONTFIX disposition,
        it should be excluded from blocking_findings and allow completion.
        """
        import subprocess

        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import github as github_pr_utils

        # Disable gates that would block completion
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR_MERGED", False)

        # Clear PR cache
        github_pr_utils._pr_cache = None
        mock_gh_cli.return_value = subprocess.CompletedProcess(
            args=["gh", "pr", "list"], returncode=0, stdout="[]", stderr=""
        )

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # P0 finding that would normally block
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'acceptance', 'critical',
                   '[{"priority": "P0", "file": "test.py", "line": 10, "description": "critical bug"}]', 1, '2025-01-01T00:00:00Z')"""
            )
            # Mark with WONTFIX disposition (stored lowercase in DB)
            conn.execute(
                """INSERT INTO finding_dispositions (task_id, file, line, disposition, reason)
                   VALUES (1, 'test.py', 10, 'wontfix', 'Out of scope for this task')"""
            )

        result = check_completion(1, db_path)
        assert result is not None
        assert result.allowed is True, f"WONTFIX disposition should allow completion: {result}"
        assert result.phase != "needs_fix", f"Phase should not be needs_fix: {result.phase}"

    def test_p0_finding_with_fixed_disposition_does_not_block(
        self, db_path, monkeypatch, mock_gh_cli
    ):
        """P0 finding with FIXED disposition does not block completion.

        Task #2688: When a P0 finding is marked with FIXED disposition,
        it should be excluded from blocking_findings and allow completion.
        """
        import subprocess

        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import github as github_pr_utils

        # Disable gates that would block completion
        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR_MERGED", False)

        # Clear PR cache
        github_pr_utils._pr_cache = None
        mock_gh_cli.return_value = subprocess.CompletedProcess(
            args=["gh", "pr", "list"], returncode=0, stdout="[]", stderr=""
        )

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', '2025-01-01T00:00:00Z')"""
            )
            # P0 finding that would normally block
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'acceptance', 'critical',
                   '[{"priority": "P0", "file": "test.py", "line": 20, "description": "security issue"}]', 1, '2025-01-01T00:00:00Z')"""
            )
            # Mark with FIXED disposition (stored lowercase in DB)
            conn.execute(
                """INSERT INTO finding_dispositions (task_id, file, line, disposition, reason)
                   VALUES (1, 'test.py', 20, 'fixed', 'Fixed in commit abc123')"""
            )

        result = check_completion(1, db_path)
        assert result is not None
        assert result.allowed is True, f"FIXED disposition should allow completion: {result}"
        assert result.phase != "needs_fix", f"Phase should not be needs_fix: {result.phase}"
