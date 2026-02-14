"""Analyze captured Claude Code hook input samples.

This script analyzes JSONL files containing real hook input data
to determine the PreToolUseHookData schema.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_jsonl_samples(file_path: Path) -> list[dict]:
    """Parse JSONL file containing hook input samples.

    Args:
        file_path: Path to the JSONL file.

    Returns:
        List of parsed JSON objects.
    """
    samples = []
    try:
        with open(file_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    samples.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning("Skipping malformed JSON at line %d: %s", line_num, e)
                    continue
    except FileNotFoundError:
        logger.debug("JSONL file not found: %s", file_path)
        return []
    return samples


def analyze_field_presence(samples: list[dict]) -> dict:
    """Analyze which fields are present in all vs. some samples.

    Args:
        samples: List of parsed hook input samples.

    Returns:
        Dict with 'required' (fields in all samples), 'optional' (fields in some),
        and 'types' (observed types for each field).
    """
    if not samples:
        return {"required": [], "optional": [], "types": {}}

    # Track field presence counts and types
    field_counts: dict[str, int] = {}
    field_types: dict[str, set[str]] = {}

    for sample in samples:
        for key, value in sample.items():
            field_counts[key] = field_counts.get(key, 0) + 1
            if key not in field_types:
                field_types[key] = set()
            field_types[key].add(type(value).__name__)

    total_samples = len(samples)
    required = [k for k, v in field_counts.items() if v == total_samples]
    optional = [k for k, v in field_counts.items() if v < total_samples]

    return {
        "required": required,
        "optional": optional,
        "types": field_types,
    }
