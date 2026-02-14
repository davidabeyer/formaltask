"""Tests for ExitCode enum.

Only tests that catch real bugs (duplicate values). Constant value tests removed —
they just duplicate the source code and wouldn't catch logic errors.
"""


class TestExitCodeEnum:
    """Test ExitCode enum structure."""

    def test_exit_code_all_values_are_unique(self):
        """All exit code values must be unique."""
        from formaltask.cli.exit_codes import ExitCode

        values = [code.value for code in ExitCode]
        assert len(values) == len(set(values)), "Duplicate exit code values found"
