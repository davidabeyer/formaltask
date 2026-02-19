"""Tests for CompletionConfig dataclass and get_effective_config function."""

import dataclasses
import json
import sqlite3

import pytest

from formaltask.core.completion_config import CompletionConfig, get_effective_config


class TestCompletionConfigDataclass:
    """Test CompletionConfig is a frozen dataclass with required fields."""

    def test_completion_config_is_frozen_dataclass(self):
        """CompletionConfig should be a frozen dataclass."""
        assert dataclasses.is_dataclass(CompletionConfig)
        # Frozen dataclasses raise FrozenInstanceError on attribute assignment
        config = CompletionConfig(
            required_reviews=["code-quality"],
            check_freshness=True,
            require_pr=False,
            require_pr_merged=False,
            documentation_required=False,
            check_docs=True,
            check_learnings=False,
            check_ac=True,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.check_freshness = False

    def test_completion_config_has_required_fields(self):
        """CompletionConfig should have all required fields from acceptance criteria."""
        fields = {f.name: f.type for f in dataclasses.fields(CompletionConfig)}
        expected_fields = {
            "required_reviews",
            "check_freshness",
            "require_pr",
            "require_pr_merged",
            "documentation_required",
            "check_docs",
            "check_learnings",
            "check_ac",
        }
        assert expected_fields.issubset(set(fields.keys()))

    def test_completion_config_field_types(self):
        """CompletionConfig fields should have correct types."""
        config = CompletionConfig(
            required_reviews=["code-quality", "security"],
            check_freshness=True,
            require_pr=False,
            require_pr_merged=False,
            documentation_required=True,
            check_docs=True,
            check_learnings=False,
            check_ac=True,
        )
        assert isinstance(config.required_reviews, list)
        assert isinstance(config.check_freshness, bool)
        assert isinstance(config.require_pr, bool)
        assert isinstance(config.require_pr_merged, bool)
        assert isinstance(config.documentation_required, bool)
        assert isinstance(config.check_docs, bool)
        assert isinstance(config.check_learnings, bool)
        assert isinstance(config.check_ac, bool)


class TestGetEffectiveConfig:
    """Test get_effective_config returns CompletionConfig with correct values."""

    def test_get_effective_config_returns_completion_config(self, db_path, repo):
        """get_effective_config should return a CompletionConfig instance."""
        repo.create_epic("test-epic", "Test epic")
        task_id = repo.create_task("test-epic", "Task 1", "Desc", ["criterion"])

        config = get_effective_config(task_id, db_path)

        assert isinstance(config, CompletionConfig)

    def test_get_effective_config_uses_global_defaults(self, db_path, repo):
        """get_effective_config should use global defaults when no task overrides."""
        repo.create_epic("test-epic", "Test epic")
        task_id = repo.create_task("test-epic", "Task 1", "Desc", ["criterion"])

        config = get_effective_config(task_id, db_path)

        # These should be the default values from rules_config.py
        assert config.required_reviews == ["acceptance"]
        assert config.check_freshness is True
        assert config.require_pr is False
        assert config.require_pr_merged is False
        assert config.check_docs is True
        assert config.check_learnings is False

    def test_get_effective_config_task_not_found_raises(self, db_path):
        """get_effective_config should raise TaskNotFoundError for missing task."""
        from formaltask.exceptions import TaskNotFoundError

        with pytest.raises(TaskNotFoundError):
            get_effective_config(9999, db_path)

    def test_get_effective_config_metadata_overrides_required_reviews(self, db_path, repo):
        """get_effective_config should use task metadata for required_reviews."""
        repo.create_epic("test-epic", "Test epic")
        task_id = repo.create_task("test-epic", "Task 1", "Desc", ["criterion"])

        # Update task metadata with custom required_reviews
        with sqlite3.connect(db_path) as conn:
            metadata = json.dumps({"required_reviews": ["code-quality", "security"]})
            conn.execute("UPDATE tasks SET metadata = ? WHERE id = ?", (metadata, task_id))
            conn.commit()

        config = get_effective_config(task_id, db_path)

        assert config.required_reviews == ["code-quality", "security"]

    def test_get_effective_config_metadata_overrides_documentation_required(self, db_path, repo):
        """get_effective_config should use task metadata for documentation_required."""
        repo.create_epic("test-epic", "Test epic")
        task_id = repo.create_task("test-epic", "Task 1", "Desc", ["criterion"])

        # Update task metadata with documentation_required=True
        with sqlite3.connect(db_path) as conn:
            metadata = json.dumps({"documentation_required": True})
            conn.execute("UPDATE tasks SET metadata = ? WHERE id = ?", (metadata, task_id))
            conn.commit()

        config = get_effective_config(task_id, db_path)

        assert config.documentation_required is True

    def test_get_effective_config_metadata_overrides_require_pr(self, db_path, repo):
        """get_effective_config should use task metadata for require_pr."""
        repo.create_epic("test-epic", "Test epic")
        task_id = repo.create_task("test-epic", "Task 1", "Desc", ["criterion"])

        # Update task metadata with require_pr=True (default is False)
        with sqlite3.connect(db_path) as conn:
            metadata = json.dumps({"require_pr": True})
            conn.execute("UPDATE tasks SET metadata = ? WHERE id = ?", (metadata, task_id))
            conn.commit()

        config = get_effective_config(task_id, db_path)

        assert config.require_pr is True

    def test_get_effective_config_metadata_overrides_require_pr_merged(self, db_path, repo):
        """get_effective_config should use task metadata for require_pr_merged."""
        repo.create_epic("test-epic", "Test epic")
        task_id = repo.create_task("test-epic", "Task 1", "Desc", ["criterion"])

        # Update task metadata with require_pr_merged=True (default is False)
        with sqlite3.connect(db_path) as conn:
            metadata = json.dumps({"require_pr_merged": True})
            conn.execute("UPDATE tasks SET metadata = ? WHERE id = ?", (metadata, task_id))
            conn.commit()

        config = get_effective_config(task_id, db_path)

        assert config.require_pr_merged is True

    def test_get_effective_config_empty_reviews_uses_default(self, db_path, repo):
        """get_effective_config should use default if required_reviews is empty list."""
        repo.create_epic("test-epic", "Test epic")
        task_id = repo.create_task("test-epic", "Task 1", "Desc", ["criterion"])

        # Update task metadata with empty required_reviews
        with sqlite3.connect(db_path) as conn:
            metadata = json.dumps({"required_reviews": []})
            conn.execute("UPDATE tasks SET metadata = ? WHERE id = ?", (metadata, task_id))
            conn.commit()

        config = get_effective_config(task_id, db_path)

        # Empty list should fall back to default
        assert config.required_reviews == ["acceptance"]
