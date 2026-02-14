"""Tests for formaltask.core.rules_builtin module (Task #2874).

Tests for BUILTIN_RULES - the 22 completion rules as Rule instances.
"""


class TestBuiltinRulesStructure:
    """Tests for BUILTIN_RULES list structure."""

    def test_builtin_rules_has_22_rules(self):
        """BUILTIN_RULES should contain exactly 22 rules."""
        from formaltask.core.rules_builtin import BUILTIN_RULES

        assert len(BUILTIN_RULES) == 22

    def test_all_rules_have_when_attribute(self):
        """All rules in BUILTIN_RULES should have a 'when' attribute."""
        from formaltask.core.rules_builtin import BUILTIN_RULES

        for i, rule in enumerate(BUILTIN_RULES):
            assert hasattr(rule, "when"), f"Rule {i} missing 'when' attribute"

    def test_all_rules_have_then_attribute(self):
        """All rules in BUILTIN_RULES should have a 'then' attribute."""
        from formaltask.core.rules_builtin import BUILTIN_RULES

        for i, rule in enumerate(BUILTIN_RULES):
            assert hasattr(rule, "then"), f"Rule {i} missing 'then' attribute"

    def test_all_rules_have_target_task_phase(self):
        """All completion rules should have target='task.phase'."""
        from formaltask.core.rules_builtin import BUILTIN_RULES

        for i, rule in enumerate(BUILTIN_RULES):
            assert rule.target == "task.phase", f"Rule {i} has target={rule.target}"

    def test_all_rules_are_rule_instances(self):
        """All items in BUILTIN_RULES should be Rule instances."""
        from formaltask.core.rules import Rule
        from formaltask.core.rules_builtin import BUILTIN_RULES

        for i, rule in enumerate(BUILTIN_RULES):
            assert isinstance(rule, Rule), f"Rule {i} is {type(rule)}, expected Rule"


class TestBuiltinRulesContent:
    """Tests for specific rule content."""

    def test_first_rule_is_status_cancelled(self):
        """First rule should handle status == cancelled."""
        from formaltask.core.rules_builtin import BUILTIN_RULES

        rule = BUILTIN_RULES[0]
        assert rule.when == "status == cancelled"
        assert rule.then == "done"

    def test_last_rule_is_catchall(self):
        """Last rule should be the catchall with priority=999."""
        from formaltask.core.rules_builtin import BUILTIN_RULES

        rule = BUILTIN_RULES[-1]
        assert rule.when == "true"
        assert rule.priority == 999

    def test_blocked_rule_exists(self):
        """A rule for blocked status should exist."""
        from formaltask.core.rules_builtin import BUILTIN_RULES

        blocked_rules = [r for r in BUILTIN_RULES if "blocked" in r.when.lower()]
        assert len(blocked_rules) >= 1

    def test_needshuman_rule_exists(self):
        """A rule for has_needshuman should exist."""
        from formaltask.core.rules_builtin import BUILTIN_RULES

        needshuman_rules = [r for r in BUILTIN_RULES if "needshuman" in r.when.lower()]
        assert len(needshuman_rules) >= 1


class TestBuiltinRulesEvaluate:
    """Tests that BUILTIN_RULES work with evaluate()."""

    def test_status_cancelled_evaluates_true(self):
        """status == 'cancelled' should evaluate True when status is cancelled."""
        from formaltask.core.rules import evaluate
        from formaltask.core.rules_builtin import BUILTIN_RULES

        rule = BUILTIN_RULES[0]
        ctx = {"status": "cancelled"}
        assert evaluate(rule.when, ctx) is True

    def test_status_cancelled_evaluates_false(self):
        """status == 'cancelled' should evaluate False when status is not cancelled."""
        from formaltask.core.rules import evaluate
        from formaltask.core.rules_builtin import BUILTIN_RULES

        rule = BUILTIN_RULES[0]
        ctx = {"status": "in_progress"}
        assert evaluate(rule.when, ctx) is False


