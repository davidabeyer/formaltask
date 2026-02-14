"""Tests for custom completion_rules overriding builtins (Task #2924).

Verifies that task-level completion_rules (stored in metadata) fire before
BUILTIN_RULES, enabling per-task gates like requiring N review rounds.

Acceptance criteria:
- First completion attempt blocked with custom rule reason
- review_rounds.code-quality correctly counts to 2
- Second completion attempt succeeds after 2nd review round
"""

import json


class TestCustomRuleBlocksFirstCompletion:
    """AC1: First completion attempt blocked with custom rule reason."""

    def test_custom_rule_blocks_with_one_review_round(self, db_path, monkeypatch):
        """Task with custom rule requiring 2 rounds blocks after only 1 round."""
        from formaltask.core import rules_config
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        rules = [
            {
                "when": "review_rounds.code-quality < 2",
                "then": "needs_review",
                "target": "task.phase",
                "priority": 1,
                "name": "Custom: 2 code-quality review rounds required",
            }
        ]
        metadata = json.dumps({
            "required_reviews": ["code-quality"],
            "completion_rules": rules,
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
            # Only 1 round of code-quality review
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.allowed is False
        assert result.phase == "needs_review"
        assert "2 code-quality review rounds required" in result.reason

    def test_custom_rule_reason_is_from_task_rule_not_builtin(self, db_path, monkeypatch):
        """The blocking reason comes from the custom rule, not a builtin."""
        from formaltask.core import rules_config
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        rules = [
            {
                "when": "review_rounds.code-quality < 2",
                "then": "needs_review",
                "target": "task.phase",
                "priority": 1,
                "name": "Custom: 2 code-quality review rounds required",
            }
        ]
        metadata = json.dumps({
            "required_reviews": ["code-quality"],
            "completion_rules": rules,
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
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        # Must be custom rule phase, not builtin phases like "awaiting_merge" or "needs_fix"
        assert result.phase == "needs_review", f"Expected custom phase, got builtin: {result.phase}"
        assert "Custom:" in result.reason


class TestReviewRoundsCounting:
    """AC2: review_rounds.code-quality correctly counts to 2."""

    def test_review_rounds_counts_max_round_per_type(self, db_path):
        """review_rounds tracks MAX(round) per review_type from task_reviews."""
        from pathlib import Path

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
            # Two rounds of code-quality
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 2, '2025-01-01T00:00:00Z')"""
            )

        state = fetch_completion_state(1, Path(db_path))
        assert state is not None
        assert state["review_rounds"]["code-quality"] == 2

    def test_review_rounds_with_one_round(self, db_path):
        """review_rounds shows 1 after single review round."""
        from pathlib import Path

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

        state = fetch_completion_state(1, Path(db_path))
        assert state["review_rounds"]["code-quality"] == 1

    def test_evaluate_review_rounds_dotted_path(self):
        """Rules DSL resolves review_rounds.code-quality via dotted path."""
        from formaltask.core.rules import evaluate

        ctx = {"review_rounds": {"code-quality": 1}}
        assert evaluate("review_rounds.code-quality < 2", ctx) is True

        ctx = {"review_rounds": {"code-quality": 2}}
        assert evaluate("review_rounds.code-quality < 2", ctx) is False

    def test_evaluate_review_rounds_missing_type(self):
        """Missing review type in review_rounds resolves to None (falsy)."""
        from formaltask.core.rules import evaluate

        ctx = {"review_rounds": {}}
        # None < 2 → _compare returns False for None
        assert evaluate("review_rounds.code-quality < 2", ctx) is False


class TestSecondCompletionSucceeds:
    """AC3: Second completion attempt succeeds after 2nd review round."""

    def test_custom_rule_passes_after_two_rounds(self, db_path, monkeypatch, mock_gh_cli):
        """Task completes after 2 code-quality rounds satisfy custom rule."""
        import subprocess

        from formaltask.core import rules_config
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import github as github_pr_utils

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)
        monkeypatch.setattr(rules_config, "REQUIRE_PR", False)
        monkeypatch.setattr(rules_config, "REQUIRE_PR_MERGED", False)

        github_pr_utils._pr_cache = None
        mock_gh_cli.return_value = subprocess.CompletedProcess(
            args=["gh", "pr", "list"], returncode=0, stdout="[]", stderr=""
        )

        rules = [
            {
                "when": "review_rounds.code-quality < 2",
                "then": "needs_review",
                "target": "task.phase",
                "priority": 1,
                "name": "Custom: 2 code-quality review rounds required",
            }
        ]
        metadata = json.dumps({
            "required_reviews": ["code-quality"],
            "completion_rules": rules,
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
            # Two rounds of clean code-quality reviews
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 2, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result.allowed is True, f"Expected allowed after 2 rounds, got: {result}"
        assert result.reason is None

    def test_transition_from_blocked_to_allowed(self, db_path, monkeypatch, mock_gh_cli):
        """First attempt blocks, second attempt (after adding round 2) succeeds."""
        import subprocess

        from formaltask.core import rules_config
        from formaltask.core.completion_check import check_completion
        from formaltask.db.connection import DatabaseConnection
        from formaltask.git import github as github_pr_utils

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)
        monkeypatch.setattr(rules_config, "REQUIRE_PR", False)
        monkeypatch.setattr(rules_config, "REQUIRE_PR_MERGED", False)

        github_pr_utils._pr_cache = None
        mock_gh_cli.return_value = subprocess.CompletedProcess(
            args=["gh", "pr", "list"], returncode=0, stdout="[]", stderr=""
        )

        rules = [
            {
                "when": "review_rounds.code-quality < 2",
                "then": "needs_review",
                "target": "task.phase",
                "priority": 1,
                "name": "Custom: 2 code-quality review rounds required",
            }
        ]
        metadata = json.dumps({
            "required_reviews": ["code-quality"],
            "completion_rules": rules,
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
            # Round 1 only
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 1, '2025-01-01T00:00:00Z')"""
            )

        # First attempt: should block
        result1 = check_completion(1, db_path)
        assert result1.allowed is False
        assert result1.phase == "needs_review"

        # Add round 2
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'code-quality', 'clean', '[]', 2, '2025-01-01T00:00:00Z')"""
            )

        # Second attempt: should succeed
        result2 = check_completion(1, db_path)
        assert result2.allowed is True


class TestCustomRulePriorityOverBuiltins:
    """Verify custom rules evaluate before builtin rules."""

    def test_custom_rule_priority_1_fires_before_builtin_catchall(self, db_path, monkeypatch):
        """Custom rule (priority=1) matches before builtin catchall (priority=999)."""
        from formaltask.core.rules import Rule
        from formaltask.core.rules_builtin import BUILTIN_RULES, apply_completion_rules

        # Custom rule that always matches
        custom = Rule(
            when="true",
            then="custom_phase",
            target="task.phase",
            priority=1,
            name="Custom rule matched",
        )
        # Custom rules go first in the list
        rules = [custom] + BUILTIN_RULES
        state = {"review_rounds": {}}

        phase, reason, allowed = apply_completion_rules(rules, state)
        # Custom rule fires first (first-match wins)
        assert phase == "custom_phase"
        assert reason == "Custom rule matched"
        assert allowed is False  # priority=1 blocks

    def test_builtin_catchall_fires_when_no_custom_rules(self, db_path):
        """Without custom rules, builtin catchall fires normally."""
        from formaltask.core.rules_builtin import BUILTIN_RULES, apply_completion_rules

        # State where no blocking conditions match except catchall
        # has_pr=True so "NOT has_pr" rule doesn't fire before catchall
        state = {
            "status": "in_progress",
            "has_reviews": True,
            "blocking_findings": [],
            "has_needshuman": False,
            "low_findings_exceeded": False,
            "missing_reviews": set(),
            "stale_reviews": set(),
            "check_docs": False,
            "check_learnings": False,
            "check_ac": False,
            "require_pr": False,
            "require_pr_merged": False,
            "has_pr": True,
        }

        phase, reason, allowed = apply_completion_rules(BUILTIN_RULES, state)
        # Should hit catchall: priority=999 → allowed=True
        assert phase == "awaiting_merge"
        assert allowed is True
