"""Stub detector - AST-based detection of empty function implementations.

Implements detecting-stubs epic from plans/epics/detecting-stubs/.
Reference: <!-- STUB-DETECTION --> pattern in root CLAUDE.md.
"""

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StubViolation:
    """Represents a detected stub function."""

    file: str
    line: int
    function: str
    pattern: str  # 'pass', 'ellipsis', 'not_implemented', 'return_none', 'empty'


def is_stub_body(body: list[ast.stmt]) -> str | None:
    """Return stub pattern name if body is a stub, else None.

    Handles leading docstrings by skipping them before analysis.
    """
    if not body:
        return "empty"

    # Skip leading docstring if present
    start_idx = 0
    if (
        isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        start_idx = 1

    # Check remaining body
    remaining = body[start_idx:]

    if not remaining:
        return "empty"

    if len(remaining) == 1:
        stmt = remaining[0]

        # Pattern: pass
        if isinstance(stmt, ast.Pass):
            return "pass"

        # Pattern: ellipsis (...)
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and stmt.value.value is ...
        ):
            return "ellipsis"

        # Pattern: raise NotImplementedError
        if isinstance(stmt, ast.Raise) and stmt.exc is not None:
            exc = stmt.exc
            # raise NotImplementedError or raise NotImplementedError(...)
            if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
                return "not_implemented"
            if isinstance(exc, ast.Call):
                func = exc.func
                if isinstance(func, ast.Name) and func.id == "NotImplementedError":
                    return "not_implemented"

        # Pattern: return None
        if isinstance(stmt, ast.Return):
            # return None or return (implicit None)
            if stmt.value is None:
                return "return_none"
            if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                return "return_none"

    return None


def is_abstract_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function has @abstractmethod decorator."""
    for decorator in node.decorator_list:
        # @abstractmethod
        if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
            return True
        # @abc.abstractmethod
        if isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod":
            return True
    return False


def is_protocol_class(cls_node: ast.ClassDef) -> bool:
    """Check if class inherits from Protocol."""
    for base in cls_node.bases:
        # Protocol
        if isinstance(base, ast.Name) and base.id == "Protocol":
            return True
        # typing.Protocol or typing_extensions.Protocol
        if isinstance(base, ast.Attribute) and base.attr == "Protocol":
            return True
    return False


def build_protocol_classes(tree: ast.AST) -> set[str]:
    """Find all Protocol class names in the AST."""
    protocol_classes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and is_protocol_class(node):
            protocol_classes.add(node.name)
    return protocol_classes


def find_parent_class(
    tree: ast.AST, func_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> str | None:
    """Find the parent class of a function node."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if item is func_node:
                    return node.name
    return None


def detect_stubs(filepath: Path) -> Iterator[StubViolation]:
    """Yield stub violations in a Python file.

    Main entry point for stub detection.
    """
    # Skip test files
    filename = filepath.name
    if filename.startswith("test_") or filename.endswith("_test.py") or filename == "conftest.py":
        return

    source = filepath.read_text()
    source_lines = source.splitlines()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    # Build set of Protocol class names
    protocol_classes = build_protocol_classes(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            pattern = is_stub_body(node.body)
            if pattern:
                # Check whitelist: @abstractmethod
                if is_abstract_method(node):
                    continue

                # Check whitelist: Protocol class methods
                parent_class = find_parent_class(tree, node)
                if parent_class and parent_class in protocol_classes:
                    continue

                # Check whitelist: # STUB: marker in preceding lines
                start_line = max(0, node.lineno - 5)
                for line_idx in range(start_line, node.lineno - 1):
                    if line_idx < len(source_lines) and "# STUB:" in source_lines[line_idx]:
                        break
                else:
                    yield StubViolation(
                        file=str(filepath),
                        line=node.lineno,
                        function=node.name,
                        pattern=pattern,
                    )
