"""Tests for formaltask.core.rules module (Task #2873).

TDD tests for the rules kernel: Rule dataclass, evaluate(), render(), apply_rules().
"""

import pytest

from formaltask.core.rules import Rule, apply_rules, evaluate, render


class TestEvaluateTruthy:
    """Tests for bare truthy evaluation."""

    def test_evaluate_true_literal_returns_true(self):
        """evaluate('true', {}) should return True."""
        assert evaluate("true", {}) is True

    def test_evaluate_false_literal_returns_false(self):
        """evaluate('false', {}) should return False."""
        assert evaluate("false", {}) is False

    def test_evaluate_context_key_truthy(self):
        """evaluate('key', {'key': True}) should return True."""
        assert evaluate("key", {"key": True}) is True

    def test_evaluate_context_key_falsy(self):
        """evaluate('key', {'key': False}) should return False."""
        assert evaluate("key", {"key": False}) is False

    def test_evaluate_missing_key_returns_false(self):
        """evaluate('missing', {}) should return False."""
        assert evaluate("missing", {}) is False


class TestEvaluateLogicalOperators:
    """Tests for AND, OR, NOT operators."""

    def test_evaluate_and_both_true(self):
        """evaluate('a AND b', ctx) where both true should return True."""
        ctx = {"a": True, "b": True}
        assert evaluate("a AND b", ctx) is True

    def test_evaluate_and_one_false(self):
        """evaluate('a AND b', ctx) where one false should return False."""
        ctx = {"a": True, "b": False}
        assert evaluate("a AND b", ctx) is False

    def test_evaluate_or_one_true(self):
        """evaluate('a OR b', ctx) where one true should return True."""
        ctx = {"a": True, "b": False}
        assert evaluate("a OR b", ctx) is True

    def test_evaluate_or_both_false(self):
        """evaluate('a OR b', ctx) where both false should return False."""
        ctx = {"a": False, "b": False}
        assert evaluate("a OR b", ctx) is False

    def test_evaluate_not_true(self):
        """evaluate('NOT a', ctx) where a is true should return False."""
        ctx = {"a": True}
        assert evaluate("NOT a", ctx) is False

    def test_evaluate_not_false(self):
        """evaluate('NOT a', ctx) where a is false should return True."""
        ctx = {"a": False}
        assert evaluate("NOT a", ctx) is True


class TestEvaluateComparisons:
    """Tests for comparison operators ==, !=, >, <, >=, <=."""

    def test_evaluate_equals_match(self):
        """evaluate('status == completed', ctx) should return True when match."""
        ctx = {"status": "completed"}
        assert evaluate("status == completed", ctx) is True

    def test_evaluate_equals_no_match(self):
        """evaluate('status == completed', ctx) should return False when no match."""
        ctx = {"status": "pending"}
        assert evaluate("status == completed", ctx) is False

    def test_evaluate_not_equals_match(self):
        """evaluate('status != pending', ctx) should return True when different."""
        ctx = {"status": "completed"}
        assert evaluate("status != pending", ctx) is True

    def test_evaluate_greater_than(self):
        """evaluate('retries > 3', ctx) should work with numbers."""
        assert evaluate("retries > 3", {"retries": 5}) is True
        assert evaluate("retries > 3", {"retries": 2}) is False

    def test_evaluate_less_than(self):
        """evaluate('count < 10', ctx) should work with numbers."""
        assert evaluate("count < 10", {"count": 5}) is True
        assert evaluate("count < 10", {"count": 15}) is False

    def test_evaluate_greater_or_equal(self):
        """evaluate('priority >= 2', ctx) should work correctly."""
        assert evaluate("priority >= 2", {"priority": 2}) is True
        assert evaluate("priority >= 2", {"priority": 3}) is True
        assert evaluate("priority >= 2", {"priority": 1}) is False

    def test_evaluate_less_or_equal(self):
        """evaluate('priority <= 2', ctx) should work correctly."""
        assert evaluate("priority <= 2", {"priority": 2}) is True
        assert evaluate("priority <= 2", {"priority": 1}) is True
        assert evaluate("priority <= 2", {"priority": 3}) is False


class TestEvaluateNoneComparisons:
    """Tests for None-safe ordered comparisons (missing keys)."""

    def test_compare_none_gte_int_returns_false(self):
        """Missing dotted path with >= should return False, not crash."""
        ctx = {"review_rounds": {}}
        assert evaluate("review_rounds.self-critique >= 2", ctx) is False

    def test_compare_none_gt_int_returns_false(self):
        """Missing dotted path with > should return False."""
        ctx = {"review_rounds": {}}
        assert evaluate("review_rounds.missing > 0", ctx) is False

    def test_compare_none_lt_int_returns_false(self):
        """Missing dotted path with < should return False."""
        ctx = {"count": None}
        assert evaluate("count < 10", ctx) is False

    def test_compare_none_lte_int_returns_false(self):
        """Missing dotted path with <= should return False."""
        ctx = {}
        assert evaluate("missing <= 5", ctx) is False

    def test_compare_none_eq_returns_false(self):
        """None == value should return False."""
        ctx = {}
        assert evaluate("missing == done", ctx) is False

    def test_compare_none_neq_returns_true(self):
        """None != value should return True."""
        ctx = {}
        assert evaluate("missing != done", ctx) is True

    def test_and_short_circuits_before_none_comparison(self):
        """AND with falsy left side should not evaluate None comparison on right."""
        ctx = {"blocking_findings": [], "review_rounds": {}}
        # blocking_findings is falsy → short-circuit → right side never evaluated
        assert evaluate("blocking_findings AND review_rounds.self-critique >= 2", ctx) is False

    def test_and_evaluates_none_comparison_when_left_truthy(self):
        """AND with truthy left side must safely evaluate None comparison on right."""
        ctx = {"blocking_findings": [{"file": "x.py"}], "review_rounds": {}}
        # blocking_findings is truthy → must evaluate right side → None >= 2 → False
        assert evaluate("blocking_findings AND review_rounds.self-critique >= 2", ctx) is False


class TestEvaluateDottedPaths:
    """Tests for dotted path resolution like task.metadata.retries."""

    def test_evaluate_dotted_path_truthy(self):
        """evaluate('task.metadata.active', ctx) should resolve nested paths."""
        ctx = {"task": {"metadata": {"active": True}}}
        assert evaluate("task.metadata.active", ctx) is True

    def test_evaluate_dotted_path_comparison(self):
        """evaluate('task.status == done', ctx) should work with dotted paths."""
        ctx = {"task": {"status": "done"}}
        assert evaluate("task.status == done", ctx) is True

    def test_evaluate_dotted_path_missing(self):
        """evaluate('task.missing.path', ctx) should return False."""
        ctx = {"task": {}}
        assert evaluate("task.missing.path", ctx) is False


class TestRender:
    """Tests for Jinja2 template rendering."""

    def test_render_simple_variable(self):
        """render('Hello {{ name }}', ctx) should substitute variable."""
        result = render("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    def test_render_multiple_variables(self):
        """render with multiple variables should substitute all."""
        result = render("{{ a }} + {{ b }} = {{ c }}", {"a": 1, "b": 2, "c": 3})
        assert result == "1 + 2 = 3"

    def test_render_undefined_raises_error(self):
        """render with undefined variable should raise UndefinedError."""
        from jinja2 import UndefinedError

        with pytest.raises(UndefinedError):
            render("Hello {{ missing }}", {})

    def test_render_nested_access(self):
        """render with nested dict access should work."""
        result = render("Status: {{ task.status }}", {"task": {"status": "done"}})
        assert result == "Status: done"


class TestApplyRules:
    """Tests for rule application."""

    def test_apply_rules_first_match_wins(self):
        """apply_rules should return first matching rule's output."""
        rules = [
            Rule(when="status == pending", then="waiting", target="user"),
            Rule(when="status == done", then="finished", target="system"),
        ]
        ctx = {"status": "done"}
        output, target = apply_rules(rules, ctx)
        assert output == "finished"
        assert target == "system"

    def test_apply_rules_no_match_returns_none(self):
        """apply_rules should return (None, None) when no rules match."""
        rules = [
            Rule(when="status == pending", then="waiting", target="user"),
        ]
        ctx = {"status": "done"}
        output, target = apply_rules(rules, ctx)
        assert output is None
        assert target is None

    def test_apply_rules_empty_list_returns_none(self):
        """apply_rules with empty rules list should return (None, None)."""
        output, target = apply_rules([], {"key": "value"})
        assert output is None
        assert target is None

    def test_apply_rules_renders_then_with_context(self):
        """apply_rules should render 'then' as Jinja2 template."""
        rules = [
            Rule(when="true", then="Hello {{ name }}", target=None),
        ]
        ctx = {"name": "World"}
        output, target = apply_rules(rules, ctx)
        assert output == "Hello World"

    def test_rule_dataclass_defaults(self):
        """Rule dataclass should have correct defaults."""
        rule = Rule(when="true", then="output")
        assert rule.target is None
        assert rule.priority == 0
        assert rule.name is None
