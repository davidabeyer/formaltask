#!/usr/bin/env python3
"""Parse ANTIREZ_AUDIT.md and report current status."""

import re
import sys
from pathlib import Path

AUDIT_FILE = Path.home() / "claude-code" / "ANTIREZ_AUDIT.md"


def parse_audit_file():
    """Parse the audit tracker and return status."""
    if not AUDIT_FILE.exists():
        print("ERROR: ANTIREZ_AUDIT.md not found")
        sys.exit(1)

    content = AUDIT_FILE.read_text()
    lines = content.split("\n")

    pending = []
    audited = []
    simplified = []
    deleted = []
    in_progress = []

    current_module = "root"

    # Pattern for module headers: ### apps/browse/ or ### cli/commands/
    module_pattern = r"^### ([a-zA-Z_/]+)/?$"
    # Pattern for file entries: | [ ] | `file.py` | 123 |
    entry_pattern = r"\| \[(.)\] \| `([^`]+)` \| (\d+) \|"

    for line in lines:
        # Check for module header
        module_match = re.match(module_pattern, line)
        if module_match:
            module_path = module_match.group(1).rstrip("/")
            # Handle special cases
            if module_path in ["paths.py (root)", "tmux.py (root)"]:
                current_module = ""
            else:
                current_module = module_path
            continue

        # Check for file entry
        entry_match = re.search(entry_pattern, line)
        if entry_match:
            status = entry_match.group(1)
            filename = entry_match.group(2)
            loc = int(entry_match.group(3))

            # Build full path
            if current_module and not filename.startswith(current_module):
                filepath = f"{current_module}/{filename}"
            else:
                filepath = filename

            entry = {"file": filepath, "loc": loc, "module": current_module or "root"}

            if status == " ":
                pending.append(entry)
            elif status == "x":
                audited.append(entry)
            elif status == "S":
                simplified.append(entry)
            elif status == "D":
                deleted.append(entry)
            elif status == "~":
                in_progress.append(entry)

    # Sort pending by LOC descending
    pending.sort(key=lambda x: x["loc"], reverse=True)

    total = len(pending) + len(audited) + len(simplified) + len(deleted) + len(in_progress)
    done = len(audited) + len(simplified) + len(deleted)

    print("=" * 60)
    print("ANTIREZ AUDIT STATUS")
    print("=" * 60)
    print()
    print(f"Progress: {done}/{total} files ({100 * done // total if total else 0}%)")
    print(f"  Audited (no changes): {len(audited)}")
    print(f"  Simplified: {len(simplified)}")
    print(f"  Deleted: {len(deleted)}")
    print(f"  In Progress: {len(in_progress)}")
    print(f"  Pending: {len(pending)}")
    print()

    if in_progress:
        print("CURRENTLY IN PROGRESS:")
        for entry in in_progress:
            print(f"  [~] {entry['file']} ({entry['loc']} LOC)")
        print()

    print("NEXT 5 TARGETS (by LOC):")
    for i, entry in enumerate(pending[:5], 1):
        print(f"  {i}. {entry['file']} ({entry['loc']} LOC)")
    print()

    # Group by top-level module
    modules = {}
    for entry in pending:
        parts = entry["file"].split("/")
        if len(parts) > 1:
            module = parts[0]
        else:
            module = "root"
        if module not in modules:
            modules[module] = {"pending": 0, "total_loc": 0}
        modules[module]["pending"] += 1
        modules[module]["total_loc"] += entry["loc"]

    print("PENDING BY MODULE:")
    for module, stats in sorted(modules.items(), key=lambda x: x[1]["total_loc"], reverse=True):
        print(f"  {module}: {stats['pending']} files, {stats['total_loc']} LOC")

    return {
        "total": total,
        "done": done,
        "pending": pending,
        "in_progress": in_progress,
    }


if __name__ == "__main__":
    parse_audit_file()
