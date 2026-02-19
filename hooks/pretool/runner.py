#!/usr/bin/env python3
"""PreToolUse hook entry point - plain function architecture."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# File-based logging for debugging
_LOG_FILE = Path.home() / ".claude" / "tmp" / "pretool-runner.log"


def _log(msg: str) -> None:
    try:
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H:%M:%S")
        with open(_LOG_FILE, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass


from hooks.pretool.phases import (
    bash_file_guard,
    doc_guard,
    epic_decompose_validator,
    feature_branch_guard,
    formaltask_db_guard,
    git_safety,
    grep_redirect,
    planning_schema_validator,
    prompt_injection,
    skill_todo_validator,
    sql_guard,
    task_context_injector,
    task_validator,
    tdd_guard,
    todowrite_validator,
    tool_redirect,
    webfetch_redirect,
)

logger = logging.getLogger(__name__)
PHASES = [
    task_context_injector.check,
    doc_guard.check,
    sql_guard.check,
    tdd_guard.check,
    task_validator.check,
    todowrite_validator.check,
    skill_todo_validator.check,
    git_safety.check,
    bash_file_guard.check,
    tool_redirect.check,
    grep_redirect.check,
    formaltask_db_guard.check,
    webfetch_redirect.check,
    feature_branch_guard.check,
    prompt_injection.check,
    epic_decompose_validator.check,
    planning_schema_validator.check,
]


def main():
    ctx, additional_context = json.load(sys.stdin), []
    tool_name = ctx.get("tool_name", "unknown")
    _log(f"PreToolUse: {tool_name}")

    for fn in PHASES:
        try:
            result = fn(ctx)
        except Exception as e:
            _log(f"  ERROR in {fn.__module__}: {e}")
            logger.debug("Phase %s error: %s", fn.__module__, e)
            continue
        if result:
            if result.get("decision") == "block":
                _log(f"  BLOCKED by {fn.__module__}")
                return print(json.dumps(result))
            if result.get("additionalContext"):
                _log(f"  additionalContext from {fn.__module__}")
                additional_context.append(result["additionalContext"])
    response = {"decision": "approve"}
    if additional_context:
        response["additionalContext"] = "\n".join(additional_context)
    print(json.dumps(response))


if __name__ == "__main__":
    main()
