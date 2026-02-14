"""Tests for CI baseline check configuration.

Note: YAML workflow structure tests were removed as they test configuration
rather than behavior. The CI pipeline itself validates workflow correctness.
Only the baseline file existence test is kept as it prevents cryptic CI failures.
"""

from tests.conftest import PROJECT_ROOT


def test_baseline_file_exists() -> None:
    """Verify baseline file referenced in pyproject.toml exists.

    This test catches a missing baseline file before CI fails cryptically.
    Unlike workflow YAML tests, this verifies a real filesystem dependency.
    """
    import tomllib

    pyproject_path = PROJECT_ROOT / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    baseline_file = config["tool"]["pyright"]["baselineFile"]
    baseline_path = PROJECT_ROOT / baseline_file

    assert baseline_path.exists(), f"Baseline file {baseline_file} not found at {baseline_path}"
