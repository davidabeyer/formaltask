"""Tests for OutputFormatter class.

Following TDD: tests written BEFORE implementation.
"""

import json
from datetime import datetime


class MockArgs:
    """Mock args object for testing OutputFormatter initialization."""

    def __init__(self, json_mode: bool = False, stream: bool = False):
        self.json = json_mode
        self.stream = stream


def test_success_json_mode():
    """success() returns valid JSON with success=True in JSON mode."""
    from formaltask.cli.output import OutputFormatter

    args = MockArgs(json_mode=True)
    formatter = OutputFormatter(args)
    data = {"task_id": 42, "status": "completed"}

    result = formatter.success(data, "Task {task_id} is {status}")

    parsed = json.loads(result)
    assert parsed["success"] is True
    assert parsed["data"] == data


def test_success_human_mode():
    """success() returns formatted human string in human mode."""
    from formaltask.cli.output import OutputFormatter

    args = MockArgs()
    formatter = OutputFormatter(args)
    data = {"task_id": 42, "status": "completed"}

    result = formatter.success(data, "Task {task_id} is {status}")

    assert result == "Task 42 is completed"


def test_success_stream_mode():
    """success() returns NDJSON with type=complete in stream mode."""
    from formaltask.cli.output import OutputFormatter

    args = MockArgs(stream=True)
    formatter = OutputFormatter(args)
    data = {"task_id": 42}

    result = formatter.success(data, "Task {task_id}")

    parsed = json.loads(result)
    assert parsed["type"] == "complete"
    assert parsed["data"] == data


def test_error_json_mode():
    """error() returns JSON envelope with error object in JSON mode."""
    from formaltask.cli.base import CLIError
    from formaltask.cli.output import OutputFormatter

    args = MockArgs(json_mode=True)
    formatter = OutputFormatter(args)
    error = CLIError("Task not found")

    result = formatter.error(error)

    parsed = json.loads(result)
    assert parsed["success"] is False
    assert "error" in parsed
    assert parsed["error"]["message"] == "Task not found"


def test_error_json_mode_with_request_id():
    """error() includes request_id when provided."""
    from formaltask.cli.base import CLIError
    from formaltask.cli.output import OutputFormatter

    args = MockArgs(json_mode=True)
    formatter = OutputFormatter(args)
    error = CLIError("Task not found")

    result = formatter.error(error, request_id="req-123")

    parsed = json.loads(result)
    assert parsed["request_id"] == "req-123"


def test_error_human_mode():
    """error() returns 'Error: {message}' string in human mode."""
    from formaltask.cli.base import CLIError
    from formaltask.cli.output import OutputFormatter

    args = MockArgs()
    formatter = OutputFormatter(args)
    error = CLIError("Task not found")

    result = formatter.error(error)

    assert result == "Error: Task not found"


def test_json_fallback_datetime():
    """datetime objects are serialized via isoformat()."""
    from formaltask.cli.output import OutputFormatter

    args = MockArgs(json_mode=True)
    formatter = OutputFormatter(args)
    dt = datetime(2024, 1, 15, 10, 30, 0)
    data = {"timestamp": dt}

    result = formatter.success(data, "Time: {timestamp}")

    parsed = json.loads(result)
    assert parsed["data"]["timestamp"] == "2024-01-15T10:30:00"


def test_json_fallback_custom_object():
    """Object with __dict__ is serialized."""
    from formaltask.cli.output import OutputFormatter

    args = MockArgs(json_mode=True)
    formatter = OutputFormatter(args)

    class Task:
        def __init__(self):
            self.id = 42
            self.title = "Test task"

    data = {"task": Task()}

    result = formatter.success(data, "Task: {task}")

    parsed = json.loads(result)
    assert parsed["data"]["task"]["id"] == 42
    assert parsed["data"]["task"]["title"] == "Test task"


def test_json_fallback_repr():
    """Objects without __dict__ fall back to repr()."""
    from formaltask.cli.output import OutputFormatter

    args = MockArgs(json_mode=True)
    formatter = OutputFormatter(args)

    # lambda has no usable __dict__, uses repr
    data = {"func": lambda x: x}

    result = formatter.success(data, "Func: {func}")

    parsed = json.loads(result)
    assert "<function" in parsed["data"]["func"]


def test_error_json_includes_code_and_exit_code():
    """error() includes code and exit_code in JSON response (Task #2414)."""
    from formaltask.cli.base import CLIError
    from formaltask.cli.exit_codes import ExitCode
    from formaltask.cli.output import OutputFormatter

    args = MockArgs(json_mode=True)
    formatter = OutputFormatter(args)
    error = CLIError("Task not found", code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    result = formatter.error(error)

    parsed = json.loads(result)
    assert parsed["success"] is False
    assert parsed["error"]["message"] == "Task not found"
    assert parsed["error"]["code"] == "NOT_FOUND"
    assert parsed["error"]["exit_code"] == ExitCode.NOT_FOUND.value
