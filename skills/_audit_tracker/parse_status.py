#!/usr/bin/env python3
"""Parse any *_AUDIT.md tracker file and report status.

Usage:
    python3 parse_status.py STYLE          # Uses ~/formaltask/STYLE_AUDIT.md
    python3 parse_status.py /path/to/file  # Explicit path
    python3 parse_status.py --json STYLE   # JSON output for scripts

Tracker Format Expected:
    | [status] | `file.py` | LOC | ... |

    Where status is:
    - [ ] Pending
    - [~] In progress
    - [x] Audited (no changes needed)
    - [S] Style fixed
    - [P] Partial (some passes done)
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TrackerEntry:
    """Single entry in a tracker file."""

    file: str
    loc: int
    status: str
    module: str = ""
    counts: dict = field(default_factory=dict)  # P0, P1, P2, P3 counts


@dataclass
class TrackerStatus:
    """Parsed status of a tracker file."""

    tracker_path: Path
    total: int = 0
    done: int = 0
    pending: list = field(default_factory=list)
    in_progress: list = field(default_factory=list)
    audited: list = field(default_factory=list)
    fixed: list = field(default_factory=list)
    partial: list = field(default_factory=list)

    @property
    def percent_done(self) -> int:
        return (100 * self.done // self.total) if self.total else 0

    def next_targets(self, n: int = 5) -> list:
        """Get next N targets by LOC (largest first)."""
        return sorted(self.pending, key=lambda x: x.loc, reverse=True)[:n]

    def by_module(self) -> dict:
        """Group pending entries by top-level module."""
        modules = {}
        for entry in self.pending:
            parts = entry.file.split("/")
            module = parts[0] if len(parts) > 1 else "root"
            if module not in modules:
                modules[module] = {"pending": 0, "total_loc": 0}
            modules[module]["pending"] += 1
            modules[module]["total_loc"] += entry.loc
        return modules


def parse_tracker(tracker_path: Path) -> TrackerStatus:
    """Parse a tracker file and return status."""
    if not tracker_path.exists():
        raise FileNotFoundError(f"Tracker not found: {tracker_path}")

    content = tracker_path.read_text()
    lines = content.split("\n")

    status = TrackerStatus(tracker_path=tracker_path)
    current_module = ""

    # Pattern for module headers: ### apps/browse/ or ### cli/commands/
    module_pattern = r"^### ([a-zA-Z_/]+)/?$"
    # Pattern for file entries: | [status] | `file.py` | LOC | ... |
    entry_pattern = r"\| \[(.)\] \| `([^`]+)` \| (\d+) \|"
    # Pattern for severity counts in remaining columns
    count_pattern = r"\| (\d*) \| (\d*) \| (\d*) \| (\d*) \|"

    for line in lines:
        # Check for module header
        module_match = re.match(module_pattern, line)
        if module_match:
            module_path = module_match.group(1).rstrip("/")
            current_module = "" if module_path == "root" else module_path
            continue

        # Check for file entry
        entry_match = re.search(entry_pattern, line)
        if entry_match:
            marker = entry_match.group(1)
            filename = entry_match.group(2)
            loc = int(entry_match.group(3))

            # Build full path
            if current_module and not filename.startswith(current_module):
                filepath = f"{current_module}/{filename}"
            else:
                filepath = filename

            # Try to extract severity counts
            counts = {}
            count_match = re.search(count_pattern, line[entry_match.end() :])
            if count_match:
                for i, level in enumerate(["P0", "P1", "P2", "P3"]):
                    val = count_match.group(i + 1)
                    if val:
                        counts[level] = int(val)

            entry = TrackerEntry(
                file=filepath,
                loc=loc,
                status=marker,
                module=current_module or "root",
                counts=counts,
            )

            # Categorize by status
            if marker == " ":
                status.pending.append(entry)
            elif marker == "x":
                status.audited.append(entry)
            elif marker == "S":
                status.fixed.append(entry)
            elif marker == "P":
                status.partial.append(entry)
            elif marker == "~":
                status.in_progress.append(entry)

    status.total = (
        len(status.pending)
        + len(status.audited)
        + len(status.fixed)
        + len(status.partial)
        + len(status.in_progress)
    )
    status.done = len(status.audited) + len(status.fixed)

    return status


def print_status(status: TrackerStatus) -> None:
    """Print human-readable status report."""
    print("=" * 60)
    print(f"AUDIT STATUS: {status.tracker_path.name}")
    print("=" * 60)
    print()
    print(f"Progress: {status.done}/{status.total} files ({status.percent_done}%)")
    print(f"  Audited (no changes): {len(status.audited)}")
    print(f"  Style fixed: {len(status.fixed)}")
    print(f"  Partial (some passes): {len(status.partial)}")
    print(f"  In Progress: {len(status.in_progress)}")
    print(f"  Pending: {len(status.pending)}")
    print()

    if status.in_progress:
        print("CURRENTLY IN PROGRESS:")
        for entry in status.in_progress:
            print(f"  [~] {entry.file} ({entry.loc} LOC)")
        print()

    if status.partial:
        print("PARTIAL (some passes done):")
        for entry in status.partial:
            print(f"  [P] {entry.file} ({entry.loc} LOC)")
        print()

    print("NEXT 5 TARGETS (by LOC):")
    for i, entry in enumerate(status.next_targets(5), 1):
        print(f"  {i}. {entry.file} ({entry.loc} LOC)")
    print()

    modules = status.by_module()
    print("PENDING BY MODULE:")
    for module, stats in sorted(modules.items(), key=lambda x: x[1]["total_loc"], reverse=True):
        print(f"  {module}: {stats['pending']} files, {stats['total_loc']} LOC")


def print_json(status: TrackerStatus) -> None:
    """Print JSON status for scripts."""
    data = {
        "tracker": str(status.tracker_path),
        "total": status.total,
        "done": status.done,
        "percent": status.percent_done,
        "counts": {
            "pending": len(status.pending),
            "in_progress": len(status.in_progress),
            "audited": len(status.audited),
            "fixed": len(status.fixed),
            "partial": len(status.partial),
        },
        "next_targets": [
            {"file": e.file, "loc": e.loc, "module": e.module} for e in status.next_targets(5)
        ],
        "by_module": status.by_module(),
    }
    print(json.dumps(data, indent=2))


def resolve_tracker_path(name_or_path: str) -> Path:
    """Resolve tracker name or path to actual file path.

    Examples:
        "STYLE" -> ~/formaltask/STYLE_AUDIT.md
        "style" -> ~/formaltask/STYLE_AUDIT.md
        "/path/to/file.md" -> /path/to/file.md
    """
    path = Path(name_or_path)
    if path.is_absolute() or path.exists():
        return path

    # Treat as skill/tracker name
    name = name_or_path.upper().replace("-", "_")
    if not name.endswith("_AUDIT"):
        name = f"{name}_AUDIT"
    return Path.home() / "claude-code" / f"{name}.md"


def main():
    args = sys.argv[1:]
    json_output = "--json" in args
    args = [a for a in args if not a.startswith("--")]

    if not args:
        print("Usage: parse_status.py [--json] <TRACKER_NAME or /path/to/tracker.md>")
        print("Examples:")
        print("  parse_status.py STYLE")
        print("  parse_status.py hunting-dead-code")
        print("  parse_status.py ~/formaltask/STYLE_AUDIT.md")
        sys.exit(1)

    tracker_path = resolve_tracker_path(args[0])

    try:
        status = parse_tracker(tracker_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if json_output:
        print_json(status)
    else:
        print_status(status)


if __name__ == "__main__":
    main()
