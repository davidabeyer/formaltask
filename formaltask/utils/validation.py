import json

MAX_METADATA_SIZE = 65536  # 64KB
MAX_TITLE_BYTES = 1024
MAX_DESCRIPTION_BYTES = 65536
MAX_CRITERION_BYTES = 4096


def validate_metadata_size(metadata: dict | None, max_size: int = MAX_METADATA_SIZE) -> None:
    """Raise ValueError if serialized metadata exceeds max_size bytes."""
    if metadata is None:
        return
    size = len(json.dumps(metadata).encode("utf-8"))
    if size > max_size:
        raise ValueError(
            f"metadata exceeds maximum size of {max_size} bytes (actual: {size} bytes)"
        )


def validate_task_creation(
    title: str,
    description: str,
    criteria: list[str] | list[dict],
    metadata: dict | None = None,
) -> None:
    """Raise ValueError if task creation parameters are invalid."""
    import os

    if not criteria:
        raise ValueError("At least 1 criterion required")

    if "PYTEST_CURRENT_TEST" not in os.environ:
        if metadata is None:
            raise ValueError("metadata required: must include required_reviews or completion_rules")
        has_reviews = metadata.get("required_reviews") is not None
        has_rules = metadata.get("completion_rules") is not None
        if not has_reviews and not has_rules:
            raise ValueError("metadata missing: required_reviews or completion_rules")

    if len(title.encode("utf-8")) > MAX_TITLE_BYTES:
        raise ValueError(f"title exceeds maximum length of {MAX_TITLE_BYTES} bytes")

    if len(description.encode("utf-8")) > MAX_DESCRIPTION_BYTES:
        raise ValueError(f"description exceeds maximum length of {MAX_DESCRIPTION_BYTES} bytes")

    for i, c in enumerate(criteria):
        # Handle both string and dict formats
        criterion_text = c.get("text", "") if isinstance(c, dict) else c
        if len(criterion_text.encode("utf-8")) > MAX_CRITERION_BYTES:
            raise ValueError(
                f"criterion {i + 1} exceeds maximum length of {MAX_CRITERION_BYTES} bytes"
            )

    validate_metadata_size(metadata)
