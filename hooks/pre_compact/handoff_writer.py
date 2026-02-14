"""Handoff file output with thread indexing.

Writes structured markdown handoffs to thread-first directories
with sequence numbers and summary slugs for maximum scannability.
"""

import json
import re
from datetime import datetime
from pathlib import Path

HANDOFF_DIR = Path.home() / ".claude" / "handoffs"
PROJECTS_DIR = Path.home() / ".claude" / "projects"


def write_thread_breadcrumb(
    thread_name: str, project_id: str, *, projects_dir: Path = PROJECTS_DIR
) -> None:
    """Write active thread to project breadcrumb file.

    Persists the active thread name so session-start can load the previous handoff.

    Args:
        thread_name: Name of the active thread.
        project_id: Claude project ID (used as directory name).
        projects_dir: Base directory for project files.
    """
    breadcrumb = projects_dir / project_id / "handoff-thread.txt"
    breadcrumb.parent.mkdir(parents=True, exist_ok=True)
    breadcrumb.write_text(thread_name)


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to filesystem-safe slug.

    Args:
        text: Text to convert to slug.
        max_length: Maximum slug length.

    Returns:
        Lowercase, hyphen-separated slug.
    """
    if not text or not text.strip():
        return "untitled"

    # Lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    # Remove special characters (keep alphanumeric and hyphens)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    # Replace spaces with hyphens
    slug = re.sub(r"\s+", "-", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    if not slug:
        return "untitled"

    # Truncate at word boundary if possible
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0]

    return slug


def get_next_sequence(thread_dir: Path) -> int:
    """Get next sequence number for a thread directory.

    Scans existing files matching NN--* pattern and returns next number.

    Args:
        thread_dir: Path to thread directory.

    Returns:
        Next sequence number (1 if directory empty or doesn't exist).
    """
    if not thread_dir.exists():
        return 1

    max_seq = 0
    pattern = re.compile(r"^(\d{2})--")

    for filepath in thread_dir.iterdir():
        match = pattern.match(filepath.name)
        if match:
            seq = int(match.group(1))
            max_seq = max(max_seq, seq)

    return max_seq + 1


def write_handoff(thread_name: str, content: dict, *, handoff_dir: Path = HANDOFF_DIR) -> Path:
    """Write handoff markdown file to thread-first directory.

    Creates directory structure: handoff_dir/thread-name/NN--YYYY-MM-DD--summary-slug.md

    Args:
        thread_name: Name of the thread (used as directory name).
        content: Dict with keys: summary, decisions, completed, pending, context, files_touched.
        handoff_dir: Base directory for handoffs.

    Returns:
        Path to the written handoff file.
    """
    now = datetime.now()
    thread_dir = handoff_dir / thread_name
    thread_dir.mkdir(parents=True, exist_ok=True)

    sequence = get_next_sequence(thread_dir)
    summary_slug = slugify(content.get("summary", ""))
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{sequence:02d}--{date_str}--{summary_slug}.md"
    filepath = thread_dir / filename

    markdown = _format_handoff_markdown(thread_name, content, sequence=sequence)

    # Atomic write
    tmp_path = filepath.with_suffix(".tmp")
    tmp_path.write_text(markdown)
    tmp_path.replace(filepath)

    # Update thread index
    relative_path = f"{thread_name}/{filename}"
    update_thread_index(thread_name, relative_path, handoff_dir=handoff_dir)

    return filepath


def _format_handoff_markdown(
    thread_name: str, content: dict, *, sequence: int | None = None
) -> str:
    """Format handoff content as markdown."""
    if sequence is not None:
        lines = [f"# {thread_name} Handoff #{sequence}\n"]
    else:
        lines = [f"# {thread_name} Handoff\n"]

    lines.append(f"**Generated:** {datetime.now().isoformat()}\n")

    lines.append("\n## Summary\n")
    lines.append(content.get("summary", "") + "\n")

    if content.get("decisions"):
        lines.append("\n## Decisions\n")
        for decision in content["decisions"]:
            lines.append(f"- {decision}\n")

    if content.get("completed"):
        lines.append("\n## Completed\n")
        for item in content["completed"]:
            lines.append(f"- {item}\n")

    if content.get("pending"):
        lines.append("\n## Pending\n")
        for item in content["pending"]:
            lines.append(f"- {item}\n")

    if content.get("context"):
        lines.append("\n## Context\n")
        lines.append(content["context"] + "\n")

    if content.get("files_touched"):
        lines.append("\n## Files Touched\n")
        for f in content["files_touched"]:
            lines.append(f"- `{f}`\n")

    return "".join(lines)


def update_thread_index(
    thread_name: str, filepath: str, *, handoff_dir: Path = HANDOFF_DIR
) -> None:
    """Update thread index with new handoff path.

    Appends filepath to the thread's history in thread-index.json.

    Args:
        thread_name: Name of the thread.
        filepath: Relative path to the handoff file (from handoff_dir).
        handoff_dir: Base directory for handoffs.
    """
    index_file = handoff_dir / "thread-index.json"

    if index_file.exists():
        data = json.loads(index_file.read_text())
    else:
        handoff_dir.mkdir(parents=True, exist_ok=True)
        data = {}

    if thread_name not in data:
        data[thread_name] = []

    data[thread_name].append(filepath)

    # Atomic write
    tmp_path = index_file.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.replace(index_file)


def find_prev_handoff(thread_name: str, *, handoff_dir: Path = HANDOFF_DIR) -> str | None:
    """Find the most recent handoff for a thread.

    Args:
        thread_name: Name of the thread.
        handoff_dir: Base directory for handoffs.

    Returns:
        Relative path to the most recent handoff, or None if not found.
    """
    index_file = handoff_dir / "thread-index.json"

    if not index_file.exists():
        return None

    data = json.loads(index_file.read_text())
    thread_history = data.get(thread_name)

    if not thread_history:
        return None

    return thread_history[-1]


def write_stub_handoff(
    thread_name: str, transcript_path: str, error: str, *, handoff_dir: Path = HANDOFF_DIR
) -> Path:
    """Write stub handoff when API call fails.

    Preserves transcript path for manual recovery.

    Args:
        thread_name: Name of the thread.
        transcript_path: Path to the original transcript for manual processing.
        error: Error message from the failed API call.
        handoff_dir: Base directory for handoffs.

    Returns:
        Path to the written stub file.
    """
    now = datetime.now()
    thread_dir = handoff_dir / thread_name
    thread_dir.mkdir(parents=True, exist_ok=True)

    sequence = get_next_sequence(thread_dir)
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{sequence:02d}--{date_str}--STUB.md"
    filepath = thread_dir / filename

    markdown = f"""# {thread_name} Handoff #{sequence} (STUB)

**Generated:** {now.isoformat()}
**Status:** Failed to generate - manual processing required

## Error

{error}

## Transcript Path

`{transcript_path}`

To manually generate this handoff, run the transcript through the handoff generator again.
"""

    # Atomic write
    tmp_path = filepath.with_suffix(".tmp")
    tmp_path.write_text(markdown)
    tmp_path.replace(filepath)

    # Update thread index
    relative_path = f"{thread_name}/{filename}"
    update_thread_index(thread_name, relative_path, handoff_dir=handoff_dir)

    return filepath
