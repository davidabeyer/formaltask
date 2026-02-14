"""String formatting utilities for task output."""


def truncate_with_ellipsis(text: str, max_length: int) -> str:
    """Truncate text to max_length, appending ellipsis if truncated.

    Args:
        text: The string to truncate.
        max_length: Maximum length of the returned string (including ellipsis).

    Returns:
        The original string if within limit, or truncated with '...' appended.
    """
    if max_length < 4:
        raise ValueError(f"max_length must be >= 4 to fit ellipsis, got {max_length}")
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_task_label(task_id: int, title: str, max_title_length: int = 50) -> str:
    """Format a task ID and title into a compact label.

    Args:
        task_id: The task identifier.
        title: The task title.
        max_title_length: Maximum length for the title portion.

    Returns:
        Formatted string like '#42: Some task title...'
    """
    truncated = truncate_with_ellipsis(title, max_title_length)
    return f"#{task_id}: {truncated}"
