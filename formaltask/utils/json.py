"""Size-limited JSON reading to prevent DOS from large inputs."""

import json
import sys
from typing import Any, BinaryIO, TextIO

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_CONFIG_FILE_SIZE = 1 * 1024 * 1024  # 1MB
MAX_STDIN_SIZE = 50 * 1024 * 1024  # 50MB


def read_json_with_limit(stream: TextIO | BinaryIO, max_size: int = MAX_FILE_SIZE) -> Any:
    """Read JSON with size limit. Raises ValueError if exceeded."""
    content = stream.read(max_size + 1)
    if len(content) > max_size:
        raise ValueError(f"JSON exceeds {max_size} byte limit ({len(content)} bytes)")
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return json.loads(content)


def read_json_from_file(filepath: str, max_size: int = MAX_FILE_SIZE) -> Any:
    """Read JSON from file with size limit."""
    with open(filepath, encoding="utf-8") as f:
        return read_json_with_limit(f, max_size)


def read_json_from_stdin(max_size: int = MAX_STDIN_SIZE) -> Any:
    """Read JSON from stdin with size limit."""
    return read_json_with_limit(sys.stdin, max_size)
