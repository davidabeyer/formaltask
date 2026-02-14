"""Tests for formula CLI commands."""

import pytest
import yaml

from formaltask.cli.commands import formula


class TestFormulaCommandAttributes:
    """Test that formula command has required attributes."""

    def test_command_name_exists(self):
        """COMMAND_NAME is defined."""
        assert hasattr(formula, "COMMAND_NAME")
        assert formula.COMMAND_NAME == "formula"

    def test_command_help_exists(self):
        """COMMAND_HELP is defined."""
        assert hasattr(formula, "COMMAND_HELP")
        assert isinstance(formula.COMMAND_HELP, str)

    def test_setup_parser_exists(self):
        """setup_parser function exists and is callable."""
        assert hasattr(formula, "setup_parser")
        assert callable(formula.setup_parser)

    def test_execute_exists(self):
        """execute function exists and is callable."""
        assert hasattr(formula, "execute")
        assert callable(formula.execute)


class TestFormulaList:
    """Test formula list subcommand."""

    def test_list_empty_directory(self, tmp_path, capsys):
        """List returns empty when no formulas exist."""
        formulas_dir = tmp_path / ".claude" / "formulas"
        formulas_dir.mkdir(parents=True)

        result = formula.list_formulas(str(formulas_dir))
        assert result == []

    def test_list_finds_yaml_files(self, tmp_path):
        """List finds all .yaml files in formulas directory."""
        formulas_dir = tmp_path / ".claude" / "formulas"
        formulas_dir.mkdir(parents=True)

        # Create test formula files
        (formulas_dir / "feature.yaml").write_text("name: feature")
        (formulas_dir / "bugfix.yaml").write_text("name: bugfix")
        (formulas_dir / "readme.md").write_text("ignore me")

        result = formula.list_formulas(str(formulas_dir))
        assert len(result) == 2
        assert "feature" in result
        assert "bugfix" in result

    def test_list_nonexistent_directory(self):
        """List handles non-existent directory gracefully."""
        result = formula.list_formulas("/nonexistent/path")
        assert result == []


class TestFormulaCook:
    """Test formula cook subcommand."""

    def test_cook_substitutes_variables(self, tmp_path):
        """Cook replaces {{ VAR }} placeholders with values."""
        formulas_dir = tmp_path / "formulas"
        formulas_dir.mkdir()

        template = {
            "name": "{{ NAME }}-epic",
            "tasks": [{"title": "Implement {{ COMPONENT }}", "priority": "{{ PRIORITY }}"}],
        }
        formula_path = formulas_dir / "test.yaml"
        formula_path.write_text(yaml.safe_dump(template))

        output_path = tmp_path / "output.yaml"
        variables = {"NAME": "auth", "COMPONENT": "login", "PRIORITY": "high"}

        formula.cook_formula(str(formula_path), variables, str(output_path))

        assert output_path.exists()
        content = yaml.safe_load(output_path.read_text())
        assert content["name"] == "auth-epic"
        assert content["tasks"][0]["title"] == "Implement login"
        assert content["tasks"][0]["priority"] == "high"

    def test_cook_invalid_formula_path(self, tmp_path):
        """Cook raises error for invalid formula path."""
        output_path = tmp_path / "output.yaml"

        with pytest.raises(FileNotFoundError):
            formula.cook_formula("/nonexistent.yaml", {}, str(output_path))

    def test_cook_creates_parent_directories(self, tmp_path):
        """Cook creates output parent directories if needed."""
        formulas_dir = tmp_path / "formulas"
        formulas_dir.mkdir()

        template = {"name": "test"}
        formula_path = formulas_dir / "test.yaml"
        formula_path.write_text(yaml.safe_dump(template))

        output_path = tmp_path / "nested" / "deep" / "output.yaml"

        formula.cook_formula(str(formula_path), {}, str(output_path))
        assert output_path.exists()


class TestFormulaBatch:
    """Test formula batch subcommand."""

    def test_batch_generates_multiple_files(self, tmp_path):
        """Batch generates one file per entity."""
        formulas_dir = tmp_path / "formulas"
        formulas_dir.mkdir()

        template = {"name": "{{ NAME }}-epic", "tasks": [{"title": "Task for {{ NAME }}"}]}
        formula_path = formulas_dir / "test.yaml"
        formula_path.write_text(yaml.safe_dump(template))

        config = {
            "formula": str(formula_path),
            "entities": [{"NAME": "auth"}, {"NAME": "payment"}, {"NAME": "search"}],
        }
        config_path = tmp_path / "batch-config.yaml"
        config_path.write_text(yaml.safe_dump(config))

        output_dir = tmp_path / "output"

        result = formula.batch_cook(str(config_path), str(output_dir))

        assert output_dir.exists()
        assert (output_dir / "auth.yaml").exists()
        assert (output_dir / "payment.yaml").exists()
        assert (output_dir / "search.yaml").exists()
        assert len(result) == 3

    def test_batch_invalid_config(self, tmp_path):
        """Batch raises error for missing config file."""
        output_dir = tmp_path / "output"

        with pytest.raises(FileNotFoundError):
            formula.batch_cook("/nonexistent.yaml", str(output_dir))

    def test_batch_missing_formula_key(self, tmp_path):
        """Batch raises error when config missing formula key."""
        config = {"entities": [{"NAME": "test"}]}
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.safe_dump(config))

        output_dir = tmp_path / "output"

        with pytest.raises(ValueError, match="formula"):
            formula.batch_cook(str(config_path), str(output_dir))


class TestFormulaHelp:
    """Test formula help output contains required subcommands."""

    def test_help_contains_list(self, capsys):
        """Help shows list subcommand."""
        import argparse

        parser = argparse.ArgumentParser()
        subparser = parser.add_subparsers()
        formula_parser = subparser.add_parser("formula")
        formula.setup_parser(formula_parser)

        # Get help text
        with pytest.raises(SystemExit):
            formula_parser.parse_args(["--help"])

        captured = capsys.readouterr()
        assert "list" in captured.out

    def test_help_contains_cook(self, capsys):
        """Help shows cook subcommand."""
        import argparse

        parser = argparse.ArgumentParser()
        subparser = parser.add_subparsers()
        formula_parser = subparser.add_parser("formula")
        formula.setup_parser(formula_parser)

        with pytest.raises(SystemExit):
            formula_parser.parse_args(["--help"])

        captured = capsys.readouterr()
        assert "cook" in captured.out

    def test_help_contains_batch(self, capsys):
        """Help shows batch subcommand."""
        import argparse

        parser = argparse.ArgumentParser()
        subparser = parser.add_subparsers()
        formula_parser = subparser.add_parser("formula")
        formula.setup_parser(formula_parser)

        with pytest.raises(SystemExit):
            formula_parser.parse_args(["--help"])

        captured = capsys.readouterr()
        assert "batch" in captured.out
