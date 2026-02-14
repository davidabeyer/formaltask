"""Rules kernel for unified rule evaluation (Task #2873).

Provides Rule dataclass, evaluate(), render(), and apply_rules() for
completion rules, orchestration rules, and prompt templates.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateSyntaxError

from formaltask.paths import get_claude_home

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """A rule with condition, output, and optional targeting."""

    when: str
    then: str
    target: str | None = None
    priority: int = 0
    name: str | None = None


def _resolve(path: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted path like 'task.metadata.retries' in context."""
    parts = path.split(".")
    value: Any = context
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
        if value is None:
            return None
    return value


def _parse_literal(s: str) -> Any:
    """Parse a literal value: 'string', 123, true/false."""
    s = s.strip()

    # Boolean literals
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False

    # Integer literals
    try:
        return int(s)
    except ValueError:
        pass

    # Float literals
    try:
        return float(s)
    except ValueError:
        pass

    # String (unquoted identifier treated as string literal for comparisons)
    return s


def _compare(a: Any, op: str, b: Any) -> bool:
    """Compare two values with the given operator."""
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    # Ordered comparisons: None means "missing" → always False
    if a is None or b is None:
        return False
    if op == ">":
        return a > b
    if op == "<":
        return a < b
    if op == ">=":
        return a >= b
    if op == "<=":
        return a <= b
    return False


# Regex patterns for parsing
_COMPARISON_PATTERN = re.compile(r"^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


def evaluate(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a condition string against a context dictionary.

    Supports:
    - Literals: 'true', 'false'
    - Logical operators: AND, OR, NOT
    - Comparison operators: ==, !=, >, <, >=, <=
    - Dotted path resolution: 'task.metadata.retries'
    - Context key lookup: 'key' returns context.get('key', False)
    """
    condition = condition.strip()

    # Handle AND (split on ' AND ' and evaluate both sides)
    if " AND " in condition:
        parts = condition.split(" AND ", 1)
        return evaluate(parts[0], context) and evaluate(parts[1], context)

    # Handle OR (split on ' OR ' and evaluate both sides)
    if " OR " in condition:
        parts = condition.split(" OR ", 1)
        return evaluate(parts[0], context) or evaluate(parts[1], context)

    # Handle NOT (prefix)
    if condition.startswith("NOT "):
        return not evaluate(condition[4:], context)

    # Handle comparison operators
    match = _COMPARISON_PATTERN.match(condition)
    if match:
        left_path = match.group(1).strip()
        op = match.group(2)
        right_raw = match.group(3).strip()

        left_value = _resolve(left_path, context)
        right_value = _parse_literal(right_raw)

        return _compare(left_value, op, right_value)

    # Handle literals
    if condition.lower() == "true":
        return True
    if condition.lower() == "false":
        return False

    # Handle dotted path or simple key lookup
    value = _resolve(condition, context)
    return bool(value)


# Jinja2 environment with StrictUndefined to catch missing variables
# Not for HTML - used for internal rule template expansion
_jinja_env = Environment(undefined=StrictUndefined)  # nosemgrep: direct-use-of-jinja2


def render(template: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 template with the given context.

    Uses StrictUndefined so missing variables raise UndefinedError.
    """
    tmpl = _jinja_env.from_string(template)
    return tmpl.render(**context)


_BUNDLED_TEMPLATES = Path(__file__).resolve().parent.parent / "workers" / "templates"
_USER_TEMPLATES = get_claude_home() / "templates"


def render_template_file(
    name: str,
    context: dict[str, Any],
    *,
    search_paths: list[str] | None = None,
) -> str:
    """Render a named Jinja2 template file from the search path.

    Search path order (first match wins):
      1. ~/.claude/templates/  (user overlay)
      2. formaltask/workers/templates/  (bundled)

    Falls back to bundled if user template has a parse error.
    """
    if search_paths is None:
        search_paths = [str(_USER_TEMPLATES), str(_BUNDLED_TEMPLATES)]

    env = Environment(  # nosemgrep: direct-use-of-jinja2
        loader=FileSystemLoader(search_paths),
        undefined=StrictUndefined,
    )

    try:
        template = env.get_template(name)
    except TemplateSyntaxError as exc:
        logger.warning(
            "Template parse error in %s: %s — falling back to bundled", exc.filename, exc
        )
        fallback_env = Environment(  # nosemgrep: direct-use-of-jinja2
            loader=FileSystemLoader([search_paths[-1]]),
            undefined=StrictUndefined,
        )
        template = fallback_env.get_template(name)

    if search_paths and template.filename:
        try:
            Path(template.filename).relative_to(search_paths[0])
            logger.debug("Using user template: %s", template.filename)
        except ValueError:
            pass

    return template.render(**context)


def apply_rules(rules: list[Rule], context: dict[str, Any]) -> tuple[str | None, str | None]:
    """Apply rules in order, return (output, target) for first match.

    Each rule's 'when' condition is evaluated against the context.
    The first rule that matches has its 'then' rendered as a Jinja2
    template and returned along with the rule's 'target'.
    """
    for rule in rules:
        if evaluate(rule.when, context):
            output = render(rule.then, context)
            return output, rule.target
    return None, None
