"""Tests for template_loader module.

Unit tests for YAML task template loading and merging.
"""



class TestLoadTemplate:
    """Tests for load_template function."""

    def test_load_template_existing_returns_dict(self, tmp_path, monkeypatch):
        """load_template('implementation') returns dict with template contents."""

        # Create a temp templates directory with a test template
        templates_dir = tmp_path / "task-templates"
        templates_dir.mkdir()
        template_file = templates_dir / "implementation.yaml"
        template_file.write_text("require_pr: true\nrequired_reviews:\n  - code-quality\n")

        # Patch TEMPLATES_DIR to use temp directory
        import formaltask.utils.template_loader as loader

        monkeypatch.setattr(loader, "TEMPLATES_DIR", templates_dir)

        result = loader.load_template("implementation")

        assert result == {"require_pr": True, "required_reviews": ["code-quality"]}

    def test_load_template_missing_returns_empty_dict(self, tmp_path, monkeypatch):
        """load_template('nonexistent') returns {} for missing template."""
        # Create empty templates directory
        templates_dir = tmp_path / "task-templates"
        templates_dir.mkdir()

        import formaltask.utils.template_loader as loader

        monkeypatch.setattr(loader, "TEMPLATES_DIR", templates_dir)

        result = loader.load_template("nonexistent")

        assert result == {}

    def test_load_template_rejects_path_traversal(self, tmp_path, monkeypatch):
        """load_template rejects path traversal attempts."""
        templates_dir = tmp_path / "task-templates"
        templates_dir.mkdir()

        import formaltask.utils.template_loader as loader

        monkeypatch.setattr(loader, "TEMPLATES_DIR", templates_dir)

        # All path traversal attempts should return empty dict
        assert loader.load_template("../../../etc/passwd") == {}
        assert loader.load_template("..\\..\\windows\\system32") == {}
        assert loader.load_template("foo/bar") == {}
        assert loader.load_template("foo\\bar") == {}


class TestMergeTemplate:
    """Tests for merge_template function."""

    def test_merge_template_explicit_overrides_template(self, tmp_path, monkeypatch):
        """Explicit metadata overrides template defaults."""
        # Create template with defaults
        templates_dir = tmp_path / "task-templates"
        templates_dir.mkdir()
        template_file = templates_dir / "implementation.yaml"
        template_file.write_text("require_pr: true\nrequired_reviews:\n  - code-quality\n")

        import formaltask.utils.template_loader as loader

        monkeypatch.setattr(loader, "TEMPLATES_DIR", templates_dir)

        # Explicit metadata should override template require_pr
        result = loader.merge_template(
            "implementation", {"require_pr": False, "custom_field": "value"}
        )

        # require_pr is overridden to False, custom_field is added
        assert result == {
            "require_pr": False,
            "required_reviews": ["code-quality"],
            "custom_field": "value",
        }
