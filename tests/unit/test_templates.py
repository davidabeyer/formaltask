"""Tests for template system: variable substitution."""


class TestSubstituteVariables:
    """Tests for substitute_variables function."""

    def test_substitute_variables_replaces_var_with_value(self):
        """{{ VAR }} in template is replaced with corresponding value from vars dict."""
        from formaltask.epics.templates import substitute_variables

        result = substitute_variables("title: {{ NAME }} task", {"NAME": "Test"})
        assert result == "title: Test task"


class TestLoadTemplate:
    """Tests for load_template function."""

    def test_load_template_parses_yaml_file(self, tmp_path):
        """load_template reads YAML file and returns parsed dict."""
        from formaltask.epics.templates import load_template

        template_file = tmp_path / "template.yaml"
        template_file.write_text("name: test\nversion: 1")

        result = load_template(str(template_file))
        assert result == {"name": "test", "version": 1}
