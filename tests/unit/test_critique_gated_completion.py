"""Tests for critique-gated task completion flow (Task #2928).

Verifies that a critique-gated task completes normally when self-critique
round 2 finds no blocking issues. The task-level escalation rule should
NOT fire because blocking_findings is false.
"""

import json


class TestCritiqueGatedEscalationRuleSkipped:
    """Escalation rule does NOT fire when blocking_findings is empty."""

    def test_escalation_rule_skipped_when_no_blocking_findings(self, db_path, monkeypatch):
        """Task-level escalation rule skipped when round 2 has no blocking findings.

        The escalation rule condition is:
          blocking_findings AND review_rounds.self-critique >= 2
        When blocking_findings is empty (falsy), the AND short-circuits.
        """
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR_MERGED", False)

        task_rules = [
            {
                "when": "blocking_findings AND review_rounds.self-critique >= 2",
                "then": "needs_escalation",
                "target": "task.phase",
                "priority": 1,
                "name": "Critique round limit. Run: ft work blocked",
            }
        ]
        metadata = json.dumps({
            "required_reviews": ["self-critique"],
            "completion_rules": task_rules,
        })

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', ?, '2025-01-01T00:00:00Z')""",
                (metadata,),
            )
            # Round 1: self-critique found P1 issue
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug"}]', 1, '2025-01-01T00:00:00Z')"""
            )
            # Worker fixed the issue (marked as fixed disposition)
            conn.execute(
                """INSERT INTO finding_dispositions (task_id, file, line, disposition, reason)
                   VALUES (1, 'a.py', 1, 'fixed', 'Fixed in subsequent commit')"""
            )
            # Round 2: self-critique clean (no new findings)
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'clean', '[]', 2, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)

        # Escalation rule should NOT fire
        assert result.phase != "needs_escalation", (
            f"Escalation rule should not fire with no blocking findings: phase={result.phase}"
        )
        # Should be allowed to complete (all gates pass)
        assert result.allowed is True, f"Expected allowed=True, got {result}"

    def test_escalation_rule_fires_when_blocking_findings_persist(self, db_path, monkeypatch):
        """Contrast: escalation rule FIRES when findings persist after round 2.

        This is the complementary case - blocking_findings still exist after
        2 rounds, so the task-level rule fires needs_escalation.
        """
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        task_rules = [
            {
                "when": "blocking_findings AND review_rounds.self-critique >= 2",
                "then": "needs_escalation",
                "target": "task.phase",
                "priority": 1,
                "name": "Critique round limit",
            }
        ]
        metadata = json.dumps({
            "required_reviews": ["self-critique"],
            "completion_rules": task_rules,
        })

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Test task', 'test', 'desc', 'in_progress', ?, '2025-01-01T00:00:00Z')""",
                (metadata,),
            )
            # Round 1 and 2 both have unfixed P1 finding
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug"}]', 1, '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug persists"}]', 2, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)

        # Escalation rule SHOULD fire
        assert result.phase == "needs_escalation"
        assert result.allowed is False


class TestBlockingFindingsEmptyWhenResolved:
    """_get_blocking_findings returns empty when all findings resolved."""

    def test_all_findings_fixed_returns_empty(self):
        """All P0/P1 findings with fixed disposition returns empty list."""
        from formaltask.core.completion_state import _get_blocking_findings

        findings = [
            {"file": "a.py", "line": 1, "priority": "P0", "description": "critical", "disposition": "fixed"},
            {"file": "b.py", "line": 2, "priority": "P1", "description": "high", "disposition": "fixed"},
        ]
        result = _get_blocking_findings(findings)
        assert result == []

    def test_all_findings_wontfix_returns_empty(self):
        """All P0/P1 findings with wontfix disposition returns empty list."""
        from formaltask.core.completion_state import _get_blocking_findings

        findings = [
            {"file": "a.py", "line": 1, "priority": "P0", "description": "critical", "disposition": "wontfix"},
            {"file": "b.py", "line": 2, "priority": "P1", "description": "high", "disposition": "wontfix"},
        ]
        result = _get_blocking_findings(findings)
        assert result == []

    def test_mixed_resolved_dispositions_returns_empty(self):
        """Mix of fixed, wontfix, and needshuman — all resolved."""
        from formaltask.core.completion_state import _get_blocking_findings

        findings = [
            {"file": "a.py", "line": 1, "priority": "P0", "description": "critical", "disposition": "fixed"},
            {"file": "b.py", "line": 2, "priority": "P1", "description": "high", "disposition": "wontfix"},
            {"file": "c.py", "line": 3, "priority": "P1", "description": "needs human", "disposition": "needshuman"},
        ]
        result = _get_blocking_findings(findings)
        assert result == []

    def test_no_findings_returns_empty(self):
        """Empty findings list returns empty."""
        from formaltask.core.completion_state import _get_blocking_findings

        assert _get_blocking_findings([]) == []


class TestCritiqueGatedFullFlow:
    """End-to-end: critique-gated task completes on clean round 2."""

    def test_critique_gated_task_completes_on_clean_round2(
        self, db_path, monkeypatch, mock_gh_cli
    ):
        """Full flow: round 1 finds issue, fix it, round 2 clean, completion succeeds.

        This is the primary acceptance criterion for Task #2928.
        """
        import subprocess

        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import github as github_pr_utils

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR", False)
        monkeypatch.setattr(completion_rules, "REQUIRE_PR_MERGED", False)

        github_pr_utils._pr_cache = None
        mock_gh_cli.return_value = subprocess.CompletedProcess(
            args=["gh", "pr", "list"], returncode=0, stdout="[]", stderr=""
        )

        task_rules = [
            {
                "when": "blocking_findings AND review_rounds.self-critique >= 2",
                "then": "needs_escalation",
                "target": "task.phase",
                "priority": 1,
                "name": "Critique round limit",
            }
        ]
        metadata = json.dumps({
            "required_reviews": ["self-critique"],
            "completion_rules": task_rules,
        })

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES ('test', 'desc', '2025-01-01T00:00:00Z')"
            )
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Critique-gated task', 'test', 'desc', 'in_progress', ?, '2025-01-01T00:00:00Z')""",
                (metadata,),
            )

            # Step 1: Round 1 self-critique finds P1 issue
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "module.py", "line": 42, "description": "Missing error handling"}]',
                   1, '2025-01-01T00:00:00Z')"""
            )

        # Verify: round 1 blocks completion
        result_round1 = check_completion(1, db_path)
        assert result_round1.allowed is False
        assert result_round1.phase == "needs_fix"

        # Step 2: Worker fixes the issue
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO finding_dispositions (task_id, file, line, disposition, reason)
                   VALUES (1, 'module.py', 42, 'fixed', 'Added error handling')"""
            )

            # Step 3: Round 2 self-critique finds no new issues
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'clean', '[]', 2, '2025-01-01T00:00:00Z')"""
            )

        # Step 4: Verify completion succeeds
        result_round2 = check_completion(1, db_path)
        assert result_round2.phase != "needs_escalation", (
            "Escalation rule should NOT fire when blocking_findings is empty"
        )
        assert result_round2.phase != "needs_fix", (
            "Should not be stuck in needs_fix when findings are resolved"
        )
        assert result_round2.allowed is True, (
            f"Completion should be allowed after clean round 2: {result_round2}"
        )
