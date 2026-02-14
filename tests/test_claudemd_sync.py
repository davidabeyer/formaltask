"""Tests for claudemd-sync.py cleanup items."""

import importlib.util
import signal
from pathlib import Path
from unittest.mock import patch

from tests.conftest import PROJECT_ROOT


def load_claudemd_sync():
    """Load claudemd-sync module from .claude/scripts."""
    script_path = PROJECT_ROOT / ".claude" / "scripts" / "claudemd-sync.py"
    spec = importlib.util.spec_from_file_location("claudemd_sync", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRootSlashGuard:
    """Tests for infinite loop guard when traversing to filesystem root."""

    def test_get_missing_docs_completes_when_py_dir_outside_root(self):
        """Line 74: while loop should terminate when reaching filesystem root.

        Bug: If a py_dir is outside the root tree, traversing up will reach '/'
        but never reach root.parent. Since Path('/').parent == Path('/'),
        current stays at '/' forever causing infinite loop.
        """
        module = load_claudemd_sync()

        def timeout_handler(signum, frame):
            raise TimeoutError("get_missing_docs hung - likely infinite loop at '/'")

        # Set 2 second timeout to detect infinite loop
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(2)

        try:
            # Scenario: root is a normal project directory
            # but find_python_directories returns a dir OUTSIDE root tree
            root = Path("/Users/test/project")
            py_dir_outside_root = Path("/tmp/other/python")

            with patch.object(
                module, "find_python_directories", return_value={py_dir_outside_root}
            ):
                # This will traverse: /tmp/other/python -> /tmp/other -> /tmp -> /
                # At /, current.parent == /, but root.parent == /Users/test
                # Without fix: infinite loop. With fix: should complete.
                result = module.get_missing_docs(root, [])
                assert isinstance(result, list)
        finally:
            signal.alarm(0)  # Cancel alarm
