"""Tests for stub_detector.py - AST-based stub detection.

TDD approach: Writing tests one at a time following Red-Green-Refactor cycle.
Reference: plans/epics/detecting-stubs/486.md
"""

from pathlib import Path


class TestDetectsPassStub:
    """Test detection of functions with only pass statement."""

    def test_detects_pass_stub(self, tmp_path: Path):
        """Detect function with only pass statement - the most basic stub pattern."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "stub_pass.py"
        test_file.write_text("""
def empty_function():
    pass
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 1
        assert violations[0].function == "empty_function"
        assert violations[0].pattern == "pass"


class TestDetectsEllipsisStub:
    """Test detection of functions with only ellipsis (...)."""

    def test_detects_ellipsis_stub(self, tmp_path: Path):
        """Detect function with only ellipsis statement."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "stub_ellipsis.py"
        test_file.write_text("""
def placeholder():
    ...
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 1
        assert violations[0].function == "placeholder"
        assert violations[0].pattern == "ellipsis"


class TestDetectsNotImplementedError:
    """Test detection of functions that raise NotImplementedError."""

    def test_detects_not_implemented_stub(self, tmp_path: Path):
        """Detect function that raises NotImplementedError."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "stub_not_impl.py"
        test_file.write_text("""
def todo_function():
    raise NotImplementedError
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 1
        assert violations[0].function == "todo_function"
        assert violations[0].pattern == "not_implemented"


class TestDetectsReturnNone:
    """Test detection of functions that only return None."""

    def test_detects_return_none_stub(self, tmp_path: Path):
        """Detect function that only returns None explicitly."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "stub_return_none.py"
        test_file.write_text("""
def noop():
    return None
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 1
        assert violations[0].function == "noop"
        assert violations[0].pattern == "return_none"


class TestDetectsEmptyBody:
    """Test detection of functions with empty body after docstring."""

    def test_detects_empty_body_stub(self, tmp_path: Path):
        """Detect function with only a docstring (empty body after)."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "stub_empty.py"
        test_file.write_text('''
def documented_stub():
    """This function does nothing."""
''')
        violations = list(detect_stubs(test_file))

        assert len(violations) == 1
        assert violations[0].function == "documented_stub"
        assert violations[0].pattern == "empty"


class TestWhitelistAbstractMethod:
    """Test that @abstractmethod decorated functions are NOT flagged."""

    def test_ignores_abstractmethod(self, tmp_path: Path):
        """@abstractmethod decorated functions should not be flagged."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "abstract_base.py"
        test_file.write_text("""
from abc import abstractmethod

class Base:
    @abstractmethod
    def must_implement(self):
        pass
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 0


class TestWhitelistProtocol:
    """Test that Protocol class methods are NOT flagged."""

    def test_ignores_protocol_methods(self, tmp_path: Path):
        """Protocol class methods should not be flagged."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "protocol_example.py"
        test_file.write_text("""
from typing import Protocol

class Processor(Protocol):
    def process(self, data: str) -> str:
        ...
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 0


class TestWhitelistStubMarker:
    """Test that functions with # STUB: marker are NOT flagged."""

    def test_ignores_stub_marker(self, tmp_path: Path):
        """Functions with # STUB: marker should not be flagged."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "marked_stub.py"
        test_file.write_text("""
# STUB: Intentionally empty for testing
def placeholder_for_testing():
    pass
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 0


class TestWhitelistTestFiles:
    """Test that test files are NOT scanned for stubs."""

    def test_ignores_test_files(self, tmp_path: Path):
        """Test files should not be flagged for stubs."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "test_something.py"
        test_file.write_text("""
def test_setup():
    pass
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 0


class TestEdgeCases:
    """Test edge cases and branches for coverage."""

    def test_handles_syntax_error_gracefully(self, tmp_path: Path):
        """Files with syntax errors should return no violations."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "bad_syntax.py"
        test_file.write_text("""
def broken(
    # missing closing paren
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 0

    def test_detects_implicit_return_none(self, tmp_path: Path):
        """Detect function that only returns without a value (implicit None)."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "implicit_return.py"
        test_file.write_text("""
def early_exit():
    return
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 1
        assert violations[0].function == "early_exit"
        assert violations[0].pattern == "return_none"

    def test_detects_async_stub(self, tmp_path: Path):
        """Async functions should also be detected."""
        from formaltask.validators.stub_detector import detect_stubs

        test_file = tmp_path / "async_stub.py"
        test_file.write_text("""
async def fetch_data():
    pass
""")
        violations = list(detect_stubs(test_file))

        assert len(violations) == 1
        assert violations[0].function == "fetch_data"
        assert violations[0].pattern == "pass"
