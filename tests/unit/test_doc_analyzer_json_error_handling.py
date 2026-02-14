"""Test JSONDecodeError handling in doc_analyzer_worker (Task #765)."""

import json
import sys

from tests.conftest import PROJECT_ROOT

# Add session_end to path
sys.path.insert(0, str(PROJECT_ROOT / "hooks" / "session_end"))


class TestWritePendingJSONErrorHandling:
    """Tests for write_pending handling of corrupted JSON files."""

    def test_write_pending_handles_corrupted_pending_json(self, tmp_path):
        """write_pending should handle corrupted pending.json gracefully.

        If pending.json exists but contains invalid JSON, it should:
        1. Not crash with JSONDecodeError
        2. Start with a fresh empty list
        3. Still successfully add the new entry
        """
        from doc_analyzer_worker import DocAnalysisResult, write_pending

        pending_dir = tmp_path / "pending"
        pending_dir.mkdir()
        pending_file = pending_dir / "pending.json"

        # Write corrupted JSON to pending file
        pending_file.write_text("{invalid json content}")

        # Create a mock result
        result = DocAnalysisResult(
            needs_update=True,
            suggestions=[],
            summary="This is a test summary for documentation analysis with enough length.",
        )

        # This should NOT raise JSONDecodeError
        write_pending(result, "test-session-123", pending_dir)

        # The file should now contain valid JSON with our entry
        assert pending_file.exists()
        data = json.loads(pending_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["session_id"] == "test-session-123"
