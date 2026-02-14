"""PostToolUse phase functions.

Plain functions for posttool hook (Task #2583).
No phase_engine dependency - simple list + loop pattern.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from .gmail_capture import capture_gmail_send
from .step_logger import log_step_enter

logger = logging.getLogger(__name__)


def is_bats_command(command: str) -> bool:
    """Check if command is a BATS test command."""
    return bool(re.search(r"\bbats\s+\S+\.bats\b", command))


def extract_test_file(command: str) -> str | None:
    """Extract test file path from BATS command."""
    match = re.search(r"(\S+\.bats)\b", command)
    return match.group(1) if match else None


def parse_tap_output(tap_output: str, test_file: str) -> dict:
    """Parse TAP output into TDD Guard testModules format."""
    tests = []
    for line in tap_output.strip().split("\n"):
        line = line.strip()
        match = re.match(r"^(ok|not ok)\s+\d+\s+(.+)$", line)
        if match:
            status = match.group(1)
            test_name = match.group(2).strip()
            tests.append(
                {
                    "name": test_name,
                    "fullName": f"{test_file}::{test_name}",
                    "state": "passed" if status == "ok" else "failed",
                }
            )

    return {"testModules": [{"moduleId": test_file, "tests": tests}]}


def run_bats_tdd_guard(ctx: dict) -> None:
    """Process BATS test results and update test.json.

    Only processes Bash tool calls that run BATS tests.
    Updates .claude/tdd-guard/data/test.json with parsed results.

    Args:
        ctx: Context dict with tool_input and tool_result
    """
    command = ctx.get("tool_input", {}).get("command", "")
    if not is_bats_command(command):
        return

    test_file = extract_test_file(command)
    if not test_file:
        return

    stdout = ctx.get("tool_result", {}).get("stdout", "")
    result = parse_tap_output(stdout, test_file)

    root = ctx.get("cwd", os.getcwd())
    output_path = Path(root) / ".claude" / "tdd-guard" / "data" / "test.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)


# Ordered list of phases (for runner to iterate)
PHASES = [
    run_bats_tdd_guard,
    capture_gmail_send,
    log_step_enter,
]

__all__ = [
    "is_bats_command",
    "extract_test_file",
    "parse_tap_output",
    "run_bats_tdd_guard",
    "capture_gmail_send",
    "log_step_enter",
    "PHASES",
]
