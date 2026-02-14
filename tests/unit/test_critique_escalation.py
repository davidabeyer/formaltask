"""Tests for self-critique escalation after 2 failed rounds (Task #2927).

Verifies the full escalation flow:
1. Task-level completion_rules with escalation condition fire after 2 rounds
2. GuardViolation message contains the rule name (instruction for worker)
3. ft work blocked transitions task to blocked_user
"""

import json

import pytest

from formaltask.core.completion_check import check_completion
from formaltask.core.rules import Rule, evaluate
from formaltask.core.rules_builtin import apply_completion_rules
from formaltask.db.connection import DatabaseConnection

# --- Helpers ---

ESCALATION_RULE = {
    "when": "blocking_findings AND review_rounds.self-critique >= 2",
    "then": "needs_escalation",
    "target": "task.phase",
    "priority": 1,
    "name": "Run: ft work blocked 'findings persist'",
}


def _insert_task_with_escalation_rules(db_path, *, status="in_progress"):
    """Insert epic + task with critique-gated completion_rules."""
    metadata = json.dumps({
        "required_reviews": ["self-critique"],
        "completion_rules": [ESCALATION_RULE],
    })
    with DatabaseConnection(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) "
            "VALUES ('esc-test', 'desc', '2025-01-01T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO tasks (title, epic_name, description, status, metadata, created_at) "
            "VALUES ('Escalation test', 'esc-test', 'desc', ?, ?, '2025-01-01T00:00:00Z')",
            (status, metadata),
        )


def _insert_self_critique_round(db_path, task_id, round_num, *, has_findings=True):
    """Insert a self-critique review round with optional P1 finding."""
    findings = (
        f'[{{"priority": "P1", "file": "a.py", "line": 1, "description": "bug round {round_num}"}}]'
        if has_findings
        else "[]"
    )
    severity = "major" if has_findings else "clean"
    with DatabaseConnection(db_path) as conn:
        conn.execute(
            "INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at) "
            "VALUES (?, 'self-critique', ?, ?, ?, '2025-01-01T00:00:00Z')",
            (task_id, severity, findings, round_num),
        )


# --- AC1: Escalation rule fires after 2 self-critique rounds with findings ---


class TestEscalationRuleFires:
    """AC1: After 2 self-critique rounds with findings, escalation rule fires."""

    def test_escalation_fires_with_2_rounds_and_findings(self, db_path, monkeypatch):
        """check_completion returns needs_escalation when 2+ rounds have blocking findings."""
        from formaltask.core import rules_config

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        _insert_task_with_escalation_rules(db_path)
        _insert_self_critique_round(db_path, 1, round_num=1)
        _insert_self_critique_round(db_path, 1, round_num=2)

        result = check_completion(1, db_path)
        assert result.phase == "needs_escalation"
        assert result.allowed is False

    def test_no_escalation_with_only_1_round(self, db_path, monkeypatch):
        """1 round is not enough to trigger escalation — falls to builtin needs_fix."""
        from formaltask.core import rules_config

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        _insert_task_with_escalation_rules(db_path)
        _insert_self_critique_round(db_path, 1, round_num=1)

        result = check_completion(1, db_path)
        # Task rule condition fails (rounds < 2), but builtin blocking_findings fires
        assert result.phase == "needs_fix"
        assert result.allowed is False

    def test_no_escalation_without_findings(self, db_path, monkeypatch):
        """2 rounds but no findings = no escalation (blocking_findings is falsy)."""
        from formaltask.core import rules_config

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        _insert_task_with_escalation_rules(db_path)
        _insert_self_critique_round(db_path, 1, round_num=1, has_findings=False)
        _insert_self_critique_round(db_path, 1, round_num=2, has_findings=False)

        result = check_completion(1, db_path)
        # No blocking findings → escalation rule doesn't fire
        assert result.phase != "needs_escalation"

    def test_task_rule_fires_before_builtin(self, db_path, monkeypatch):
        """Task-level rules evaluated before BUILTIN_RULES (priority ordering)."""
        from formaltask.core import rules_config

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        _insert_task_with_escalation_rules(db_path)
        _insert_self_critique_round(db_path, 1, round_num=1)
        _insert_self_critique_round(db_path, 1, round_num=2)

        result = check_completion(1, db_path)
        # Must be needs_escalation (task rule), NOT needs_fix (builtin)
        assert result.phase == "needs_escalation"


# --- AC2: GuardViolation message contains rule name instruction ---


class TestGuardViolationContainsRuleName:
    """AC2: GuardViolation message contains the rule name instruction."""

    def test_guard_violation_message_is_rule_name(self, db_path, monkeypatch):
        """GuardViolation.message should contain the escalation rule's name field."""
        from formaltask.core import rules_config

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        _insert_task_with_escalation_rules(db_path)
        _insert_self_critique_round(db_path, 1, round_num=1)
        _insert_self_critique_round(db_path, 1, round_num=2)

        result = check_completion(1, db_path)
        # The reason field carries the rule's name
        assert result.reason == ESCALATION_RULE["name"]

    def test_completion_check_reason_propagates_to_guard_violation(self, db_path, monkeypatch):
        """task_complete raises GuardViolation with result.reason as message."""
        from unittest.mock import patch

        from formaltask.cli.commands.task_complete import _complete_task
        from formaltask.core import rules_config
        from formaltask.tasks.guards import GuardViolation

        monkeypatch.setattr(rules_config, "CHECK_FRESHNESS", False)

        _insert_task_with_escalation_rules(db_path)
        _insert_self_critique_round(db_path, 1, round_num=1)
        _insert_self_critique_round(db_path, 1, round_num=2)

        # Add a commit so evidence guard passes
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO commits (task_id, commit_hash, commit_message) "
                "VALUES (1, 'abc123def456abc123def456abc123def456abcdef', 'test commit')"  # pragma: allowlist secret
            )

        # Mock _should_skip_review_gates to return False (we want the review gates to fire)
        with (
            patch(
                "formaltask.cli.commands.task_complete._should_skip_review_gates",
                return_value=(False, "task-2927"),
            ),
            pytest.raises(GuardViolation) as exc_info,
        ):
            _complete_task(1, db_path, no_evidence=True)

        assert ESCALATION_RULE["name"] in exc_info.value.message


# --- AC3: ft work blocked transitions to blocked_user ---


class TestBlockedTransition:
    """AC3: Worker successfully transitions to blocked_user via ft work blocked."""

    def test_blocked_command_transitions_to_blocked_user(self, db_path, monkeypatch):
        """ft work blocked sets status=blocked_user and blocked_question."""
        from types import SimpleNamespace

        from formaltask.cli.commands import blocked as blocked_cmd

        _insert_task_with_escalation_rules(db_path)

        # Mock get_task_id_from_session to return task 1
        monkeypatch.setattr(
            "formaltask.cli.commands.blocked.get_task_id_from_session", lambda: 1
        )
        monkeypatch.setattr(
            "formaltask.cli.commands.blocked.get_db_path", lambda: db_path
        )

        args = SimpleNamespace(question="findings persist", db_path=db_path)
        exit_code = blocked_cmd.execute(args)

        assert exit_code == 0

        # Verify status changed to blocked_user
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, blocked_question FROM tasks WHERE id = 1")
            row = cursor.fetchone()

        assert row[0] == "blocked_user"
        assert row[1] == "findings persist"

    def test_blocked_command_rejects_non_in_progress(self, db_path, monkeypatch):
        """ft work blocked only works from in_progress or blocked_user status."""
        from types import SimpleNamespace

        from formaltask.cli.commands import blocked as blocked_cmd
        from formaltask.cli.exit_codes import ExitCode

        _insert_task_with_escalation_rules(db_path, status="open")

        monkeypatch.setattr(
            "formaltask.cli.commands.blocked.get_task_id_from_session", lambda: 1
        )
        monkeypatch.setattr(
            "formaltask.cli.commands.blocked.get_db_path", lambda: db_path
        )

        args = SimpleNamespace(question="should fail", db_path=db_path)
        exit_code = blocked_cmd.execute(args)

        assert exit_code == ExitCode.INVALID_STATE


# --- Unit tests for rules kernel evaluate() with escalation condition ---


class TestEvaluateEscalationCondition:
    """Unit tests for the specific escalation condition in rules.evaluate()."""

    def test_and_with_dotted_path_gte_true(self):
        """blocking_findings AND review_rounds.self-critique >= 2 evaluates True."""
        ctx = {
            "blocking_findings": [{"file": "a.py"}],
            "review_rounds": {"self-critique": 2},
        }
        assert evaluate("blocking_findings AND review_rounds.self-critique >= 2", ctx) is True

    def test_and_with_dotted_path_gte_false_low_rounds(self):
        """False when rounds < 2."""
        ctx = {
            "blocking_findings": [{"file": "a.py"}],
            "review_rounds": {"self-critique": 1},
        }
        assert evaluate("blocking_findings AND review_rounds.self-critique >= 2", ctx) is False

    def test_and_with_empty_findings_false(self):
        """False when blocking_findings is empty list (falsy)."""
        ctx = {
            "blocking_findings": [],
            "review_rounds": {"self-critique": 3},
        }
        assert evaluate("blocking_findings AND review_rounds.self-critique >= 2", ctx) is False

    def test_and_with_missing_review_rounds_false(self):
        """False when review_rounds.self-critique is missing (None >= 2 = False)."""
        ctx = {
            "blocking_findings": [{"file": "a.py"}],
            "review_rounds": {},
        }
        assert evaluate("blocking_findings AND review_rounds.self-critique >= 2", ctx) is False


class TestApplyCompletionRulesEscalation:
    """Test apply_completion_rules with escalation rule."""

    def test_escalation_rule_returns_correct_tuple(self):
        """apply_completion_rules returns (needs_escalation, rule_name, False)."""
        rules = [Rule(**ESCALATION_RULE)]
        state = {
            "blocking_findings": [{"file": "a.py", "priority": "P1"}],
            "review_rounds": {"self-critique": 2},
        }
        phase, reason, allowed = apply_completion_rules(rules, state)
        assert phase == "needs_escalation"
        assert reason == ESCALATION_RULE["name"]
        assert allowed is False
