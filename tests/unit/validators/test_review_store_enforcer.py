"""Tests for review_store_enforcer Stop hook validator.

Task #2834: Enforces code-reviewer subagent stores review before exiting.
"""


class TestReviewStoreEnforcer:
    """Tests for check() function."""

    def test_blocks_when_no_review_store_in_transcript(self, tmp_path):
        """Should block if transcript has no review store command."""
        from formaltask.validators.review_store_enforcer import check

        # Create transcript without review store
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"type": "tool_use", "name": "Read"}\n'
            '{"type": "tool_use", "name": "Grep"}\n'
        )

        result = check({"transcript_path": str(transcript)})

        assert result is not None
        assert result["decision"] == "block"
        assert "review store" in result["reason"]

    def test_allows_when_review_store_called(self, tmp_path):
        """Should allow if transcript contains review store command."""
        from formaltask.validators.review_store_enforcer import check

        # Create transcript with review store
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"type": "tool_use", "name": "Read"}\n'
            '{"type": "tool_use", "name": "Bash", "tool_input": {"command": "ft review store \'{}\'"}}\n'
        )

        result = check({"transcript_path": str(transcript)})

        assert result is None

    def test_allows_when_python_module_review_store_called(self, tmp_path):
        """Should allow python3 -m formaltask.cli.pm review store variant."""
        from formaltask.validators.review_store_enforcer import check

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"type": "tool_use", "name": "Bash", "tool_input": {"command": "python3 -m formaltask.cli.pm review store \'{}\'"}}\n'
        )

        result = check({"transcript_path": str(transcript)})

        assert result is None

    def test_allows_when_no_transcript_path(self):
        """Should fail open if no transcript_path provided."""
        from formaltask.validators.review_store_enforcer import check

        result = check({})

        assert result is None

    def test_allows_when_transcript_not_found(self, tmp_path):
        """Should fail open if transcript file doesn't exist."""
        from formaltask.validators.review_store_enforcer import check

        result = check({"transcript_path": str(tmp_path / "nonexistent.jsonl")})

        assert result is None
