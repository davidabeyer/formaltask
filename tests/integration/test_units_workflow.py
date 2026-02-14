"""Integration tests for units workflow (Task #2893).

Validates the full workflow:
1. ft defer creates task with required_reviews for critique-gated tasks
2. Existing missing_reviews gate blocks until self-critique review done
3. Existing blocking_findings gate blocks on P0/P1 findings
4. Formula files use Jinja {{ var }} syntax (not $VAR)
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from formaltask.cli.commands.defer import execute
from formaltask.core.rules_builtin import BUILTIN_RULES, apply_completion_rules
from formaltask.db.connection import DatabaseConnection
from formaltask.epics import create_epic
from formaltask.epics.templates import substitute_variables


class TestDeferCreatesSelfCritiqueReview:
    """Test that ft defer creates task with required_reviews=['self-critique'] for critique-gated tasks."""

    def test_defer_sets_required_reviews_for_critique_gated(self, db_path, tmp_path):
        """ft defer with task_type=critique-gated sets required_reviews=['self-critique'] in metadata."""
        create_epic(db_path=db_path, name="test-epic", description="Test epic")

        source_file = tmp_path / "src" / "example.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("def foo():\n    pass\n")

        with patch("formaltask.cli.commands.defer.get_task_id_from_session", return_value=None):
            import argparse

            args = argparse.Namespace(
                file=str(source_file),
                line=1,
                title="Fix edge case",
                task_type="critique-gated",
                epic="test-epic",
                spawn=False,
                db_path=db_path,
            )
            exit_code = execute(args)

        assert exit_code == 0

        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata FROM tasks WHERE epic_name = ?", ("test-epic",))
            row = cursor.fetchone()

        assert row is not None
        metadata = json.loads(row[0])
        assert metadata.get("task_type") == "critique-gated"
        assert metadata.get("required_reviews") == ["self-critique"]
        # Old workflow keys should NOT be present
        assert "workflow_phase" not in metadata
        assert "workflow_events" not in metadata

    def test_defer_standard_task_no_required_reviews(self, db_path, tmp_path):
        """ft defer with task_type=standard does NOT set required_reviews."""
        create_epic(db_path=db_path, name="test-epic", description="Test epic")

        source_file = tmp_path / "src" / "example.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("def foo():\n    pass\n")

        with patch("formaltask.cli.commands.defer.get_task_id_from_session", return_value=None):
            import argparse

            args = argparse.Namespace(
                file=str(source_file),
                line=1,
                title="Fix standard issue",
                task_type="standard",
                epic="test-epic",
                spawn=False,
                db_path=db_path,
            )
            exit_code = execute(args)

        assert exit_code == 0

        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata FROM tasks WHERE epic_name = ?", ("test-epic",))
            row = cursor.fetchone()

        metadata = json.loads(row[0])
        assert "required_reviews" not in metadata

    def test_missing_reviews_gate_blocks_without_self_critique(self, db_path):
        """missing_reviews gate blocks completion when self-critique review is missing."""
        # State simulating a critique-gated task with required self-critique but no review done
        state = {
            "status": "in_progress",
            "closed": False,
            "blocked": False,
            "has_reviews": True,
            "blocking_findings": [],
            "has_needshuman": False,
            "low_findings_exceeded": False,
            "missing_reviews": {"self-critique"},
            "missing_reason": "Missing required reviews: self-critique",
            "stale_reviews": set(),
            "check_ac": False,
            "check_docs": False,
            "check_learnings": False,
            "require_pr": False,
            "require_pr_merged": False,
            "has_pr": True,
            "pr_merged": False,
        }

        phase, reason, allowed = apply_completion_rules(BUILTIN_RULES, state)

        assert allowed is False
        assert "self-critique" in (reason or "")


class TestCompletionPolicyRoundCap:
    """Test end-to-end round-cap completion policy behavior."""

    def test_round_cap_blocks_after_threshold(self, db_path, monkeypatch):
        """Task with completion_rules blocks when review_rounds >= threshold."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        create_epic(db_path=db_path, name="test-epic", description="Test epic")

        rules = [
            {
                "when": "blocking_findings AND review_rounds.self-critique >= 2",
                "then": "needs_escalation",
                "target": "task.phase",
                "priority": 1,
                "name": "Critique round limit. Run: ft work blocked 'P0/P1 findings persist'",
            }
        ]
        metadata = json.dumps({
            "required_reviews": ["self-critique"],
            "completion_rules": rules,
        })

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Fix edge case', 'test-epic', 'desc', 'in_progress', ?, '2025-01-01T00:00:00Z')""",
                (metadata,),
            )
            # Round 1 self-critique with P1 finding
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug found"}]', 1, '2025-01-01T00:00:00Z')"""
            )
            # Round 2 self-critique with P1 finding still present
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug persists"}]', 2, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result is not None
        assert result.allowed is False
        assert result.phase == "needs_escalation"

    def test_round_cap_allows_before_threshold(self, db_path, monkeypatch):
        """Task with completion_rules allows normal flow before threshold."""
        from formaltask.core import rules_config as completion_rules
        from formaltask.core.completion_check import check_completion

        monkeypatch.setattr(completion_rules, "CHECK_FRESHNESS", False)

        create_epic(db_path=db_path, name="test-epic", description="Test epic")

        rules = [
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
            "completion_rules": rules,
        })

        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO tasks (title, epic_name, description, status, metadata, created_at)
                   VALUES ('Fix edge case', 'test-epic', 'desc', 'in_progress', ?, '2025-01-01T00:00:00Z')""",
                (metadata,),
            )
            # Only 1 round of self-critique with P1 finding
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, round, reviewed_at)
                   VALUES (1, 'self-critique', 'major',
                   '[{"priority": "P1", "file": "a.py", "line": 1, "description": "bug found"}]', 1, '2025-01-01T00:00:00Z')"""
            )

        result = check_completion(1, db_path)
        assert result is not None
        assert result.allowed is False
        # Should be builtin needs_fix, NOT needs_escalation (only 1 round)
        assert result.phase == "needs_fix"


class TestJinjaTemplateRendering:
    """Test Jinja template rendering in templates.py and instructions.py."""

    def test_substitute_variables_uses_jinja_syntax(self):
        """templates.py substitute_variables uses Jinja {{ var }} syntax."""
        template = "Hello {{ name }}, you have {{ count }} items"
        vars_dict = {"name": "Alice", "count": 5}

        result = substitute_variables(template, vars_dict)

        assert result == "Hello Alice, you have 5 items"

    def test_substitute_variables_handles_nested_access(self):
        """substitute_variables handles nested dict access with Jinja."""
        template = "Epic: {{ epic.name }}, Task: {{ task.title }}"
        vars_dict = {"epic": {"name": "auth-epic"}, "task": {"title": "Login"}}

        result = substitute_variables(template, vars_dict)

        assert result == "Epic: auth-epic, Task: Login"



class TestFormulaFilesSyntax:
    """Test AC #4: Formula files use {{ var }} syntax (no $VAR remains)."""

    def test_no_dollar_var_syntax_in_formula_files(self):
        """No $VAR syntax remains in .claude/formulas/*.yaml files."""
        formulas_dir = Path(__file__).parent.parent.parent / ".claude" / "formulas"

        if not formulas_dir.exists():
            pytest.skip("No formulas directory")

        yaml_files = list(formulas_dir.glob("*.yaml"))
        assert len(yaml_files) > 0, "Should have at least one formula file"

        violations = []
        import re

        dollar_var_pattern = re.compile(r"\$[A-Z_]+")

        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            matches = dollar_var_pattern.findall(content)
            if matches:
                violations.append((yaml_file.name, matches))

        assert not violations, f"Formula files contain $VAR syntax: {violations}"
