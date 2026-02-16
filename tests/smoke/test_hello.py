import subprocess
import sys


def test_hello_prints_hello_10_times():
    result = subprocess.run(
        [sys.executable, "tests/smoke/hello.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    lines = result.stdout.strip().split("\n")
    assert lines == ["hello"] * 10
