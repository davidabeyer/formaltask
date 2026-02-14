"""Template system for YAML epics.

Provides:
- substitute_variables: Replace {{ VAR }} with values from a dict
- load_template: Load and parse template YAML file
"""

import yaml

from formaltask.core.rules import render


def substitute_variables(template: str, vars: dict) -> str:
    """Replace {{ VAR }} in template with values from vars dict.

    Uses Jinja2 templating via render() from formaltask.core.rules.

    Args:
        template: String containing {{ VAR }} placeholders
        vars: Dict mapping variable names to values

    Returns:
        String with all {{ VAR }} placeholders replaced
    """
    return render(template, vars)


def load_template(path: str) -> dict:
    """Load and parse a template YAML file.

    Args:
        path: Path to the template YAML file

    Returns:
        Parsed template as a dict
    """
    with open(path) as f:
        return yaml.safe_load(f)
