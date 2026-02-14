#!/usr/bin/env python3
"""Generate initial tracker file by scanning codebase.

Usage:
    # Generate style audit tracker for all Python files
    python3 create_tracker.py --skill=style --target=formaltask/

    # Generate with module granularity (for dead code hunts)
    python3 create_tracker.py --skill=dead-code --target=formaltask/ --granularity=module

    # Generate for tests only
    python3 create_tracker.py --skill=test-bloat --target=tests/

    # Update existing tracker with new files only (non-destructive)
    python3 create_tracker.py --skill=style --target=formaltask/ --update-only

    # Dry run to preview
    python3 create_tracker.py --skill=style --target=formaltask/ --dry-run
"""

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileEntry:
    """A file to track."""

    path: str
    loc: int
    module: str


# Tracker templates by skill type
TEMPLATES = {
    "style": {
        "title": "Style Audit Tracker",
        "goal": "Consistent, Pythonic code across the codebase.",
        "philosophy": "Naming → Typing → Pythonic → Organization → Documentation → Modernization",
        "checklist": """
1. **Naming:** Self-documenting? Single letters, abbrevs, inconsistency
2. **Typing:** Complete and correct? Missing hints, `Any`, wrong types
3. **Pythonic:** Would senior Pythonista write this? `range(len())`, non-idiomatic
4. **Organization:** Clean structure? Import order, `__all__`, boundaries
5. **Documentation:** Understandable? Missing docstrings, stale comments
6. **Modernization:** Current Python? `os.path` vs pathlib, `%` vs f-string
""",
        "columns": ["Status", "File", "LOC", "P0", "P1", "P2", "P3", "Notes"],
        "severity": """
| Level | Criteria | Example |
|-------|----------|---------|
| P0 | Causes bugs NOW | Type says `str`, returns `None` |
| P1 | Maintenance pain | Inconsistent naming |
| P2 | Readability | Missing docstring |
| P3 | Style preference | `os.path` vs pathlib |
""",
    },
    "antirez": {
        "title": "Antirez Audit Tracker",
        "goal": "Delete > Simplify > Inline > Abstract.",
        "philosophy": "Every line is a liability. Justify existence or delete.",
        "checklist": """
For each file, ask:
1. **Should this file exist?** Could it be 50 lines in an existing module?
2. **For each function:** DELETE, INLINE, SIMPLIFY, or KEEP?
3. **Quality issues:** Deep nesting, magic methods, unclear names
""",
        "columns": ["Status", "File", "LOC", "Deletable", "Simplify", "Quality", "Notes"],
        "severity": None,
    },
    "dead-code": {
        "title": "Dead Code Hunt Tracker",
        "goal": "Find and delete code that serves no purpose.",
        "philosophy": "Every line must answer YES to: Does deleting this break something real?",
        "checklist": """
Hunt for:
1. **Unused imports:** Imported but never referenced
2. **Orphan functions:** Defined but never called
3. **Unreachable branches:** Code that can never execute
4. **Commented code:** Left for reference but pollutes
""",
        "columns": ["Status", "File", "LOC", "Unused", "Orphan", "Unreachable", "Notes"],
        "severity": None,
    },
    "test-bloat": {
        "title": "Test Bloat Hunt Tracker",
        "goal": "Tests that don't earn their keep get deleted.",
        "philosophy": "Would deleting this test let a real bug slip through? No → delete it.",
        "checklist": """
Hunt for:
1. **Mock hydras:** Mocks everything including SUT
2. **Implementation prisoners:** Break on refactor
3. **Redundant twins:** Same behavior tested twice
4. **Setup novels:** 50 lines setup, 1 assertion
""",
        "columns": ["Status", "File", "LOC", "Mocks", "Redundant", "Setup", "Notes"],
        "severity": None,
    },
}


def count_lines(filepath: Path) -> int:
    """Count non-empty, non-comment lines in a Python file."""
    try:
        content = filepath.read_text()
        lines = content.split("\n")
        count = 0
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            # Skip empty lines
            if not stripped:
                continue
            # Track docstrings
            if '"""' in stripped or "'''" in stripped:
                # Toggle docstring state (simplified)
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            # Skip comments
            if stripped.startswith("#"):
                continue
            count += 1
        return count
    except Exception:
        return 0


def scan_files(
    target: Path,
    pattern: str = "**/*.py",
    exclude: list | None = None,
) -> list[FileEntry]:
    """Scan target directory for files matching pattern."""
    exclude = exclude or ["__pycache__", ".git", "venv", ".venv", "node_modules"]

    entries = []
    for filepath in target.glob(pattern):
        # Skip excluded paths
        if any(ex in str(filepath) for ex in exclude):
            continue

        # Get relative path from target
        rel_path = filepath.relative_to(target)

        # Determine module (top-level directory)
        parts = rel_path.parts
        module = parts[0] if len(parts) > 1 else "root"

        loc = count_lines(filepath)
        entries.append(FileEntry(path=str(rel_path), loc=loc, module=module))

    return entries


def scan_modules(target: Path, exclude: list | None = None) -> list[FileEntry]:
    """Scan for modules (directories with __init__.py) instead of files."""
    exclude = exclude or ["__pycache__", ".git", "venv", ".venv", "node_modules"]

    entries = []
    for init in target.glob("**/__init__.py"):
        module_dir = init.parent

        # Skip excluded paths
        if any(ex in str(module_dir) for ex in exclude):
            continue

        # Get relative path
        rel_path = module_dir.relative_to(target)
        if str(rel_path) == ".":
            continue  # Skip root

        # Count total LOC in module
        total_loc = sum(count_lines(f) for f in module_dir.glob("*.py"))

        # Determine parent module
        parts = rel_path.parts
        parent = parts[0] if len(parts) > 1 else "root"

        entries.append(FileEntry(path=str(rel_path), loc=total_loc, module=parent))

    return entries


def group_by_priority(entries: list[FileEntry]) -> dict[str, list[FileEntry]]:
    """Group entries by LOC priority tiers."""
    tiers = {
        "Priority 1: Files > 500 LOC": [],
        "Priority 2: Files 200-500 LOC": [],
        "Priority 3: Files < 200 LOC": [],
    }

    for entry in sorted(entries, key=lambda e: e.loc, reverse=True):
        if entry.loc > 500:
            tiers["Priority 1: Files > 500 LOC"].append(entry)
        elif entry.loc >= 200:
            tiers["Priority 2: Files 200-500 LOC"].append(entry)
        else:
            tiers["Priority 3: Files < 200 LOC"].append(entry)

    return tiers


def generate_tracker(
    skill: str,
    entries: list[FileEntry],
) -> str:
    """Generate tracker markdown content."""
    template = TEMPLATES.get(skill, TEMPLATES["style"])
    total_loc = sum(e.loc for e in entries)

    lines = [
        f"# {template['title']}",
        "",
        f"**Goal:** {template['goal']}",
        f"**Philosophy:** {template['philosophy']}",
        f"**Total:** ~{len(entries)} files, ~{total_loc:,} LOC",
        "",
        "## Status Legend",
        "",
        "- `[ ]` Pending",
        "- `[~]` In progress",
        "- `[x]` Audited (no changes needed)",
        "- `[S]` Style fixed",
        "- `[P]` Partial (some passes done)",
        "",
    ]

    if template.get("severity"):
        lines.extend(
            [
                "## Severity Legend",
                "",
                template["severity"],
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "## Checklist",
            "",
            template["checklist"],
            "",
            "---",
            "",
        ]
    )

    # Group by priority tiers
    tiers = group_by_priority(entries)

    for tier_name, tier_entries in tiers.items():
        if not tier_entries:
            continue

        lines.append(f"## {tier_name}")
        lines.append("")

        # Group by module within tier
        by_module = defaultdict(list)
        for entry in tier_entries:
            by_module[entry.module].append(entry)

        for module in sorted(by_module.keys()):
            module_entries = by_module[module]
            lines.append(f"### {module}/")
            lines.append("")

            # Table header
            cols = template["columns"]
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("|" + "|".join(["------" if c == "Status" else "---" for c in cols]) + "|")

            # Table rows
            for entry in sorted(module_entries, key=lambda e: e.loc, reverse=True):
                # Use full relative path for unambiguous updates
                row = f"| [ ] | `{entry.path}` | {entry.loc} |"
                # Add empty columns for remaining
                row += " | " * (len(cols) - 4) + " |"
                lines.append(row)

            lines.append("")

    # Audit log section
    lines.extend(
        [
            "---",
            "",
            "## Audit Log",
            "",
            "| Date | File | Action | Issue Count | Notes |",
            "|------|------|--------|-------------|-------|",
            "| | | | | |",
            "",
        ]
    )

    return "\n".join(lines)


def load_existing_files(tracker_path: Path) -> set[str]:
    """Load files already in tracker to avoid duplicates during update."""
    if not tracker_path.exists():
        return set()

    import re

    content = tracker_path.read_text()
    # Find all `filename.py` entries
    pattern = r"`([^`]+\.py)`"
    return set(re.findall(pattern, content))


def main():
    parser = argparse.ArgumentParser(description="Generate audit tracker file")
    parser.add_argument(
        "--skill", required=True, help="Skill type: style, antirez, dead-code, test-bloat"
    )
    parser.add_argument("--target", required=True, help="Directory to scan")
    parser.add_argument(
        "--output", help="Output file path (default: {PROJECT_ROOT}/{SKILL}_AUDIT.md)"
    )
    parser.add_argument(
        "--granularity", choices=["file", "module"], default="file", help="Track files or modules"
    )
    parser.add_argument("--pattern", default="**/*.py", help="Glob pattern for files")
    parser.add_argument(
        "--update-only", action="store_true", help="Only add new files to existing tracker"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")

    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Target not found: {target}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        output = Path(args.output)
    else:
        skill_name = args.skill.upper().replace("-", "_")
        output = Path.home() / "claude-code" / f"{skill_name}_AUDIT.md"

    # Scan files or modules
    if args.granularity == "module":
        entries = scan_modules(target)
    else:
        entries = scan_files(target, args.pattern)

    if not entries:
        print(f"No files found in {target} matching {args.pattern}", file=sys.stderr)
        sys.exit(1)

    # Handle update-only mode
    if args.update_only:
        existing = load_existing_files(output)
        entries = [e for e in entries if e.path.split("/")[-1] not in existing]
        if not entries:
            print("No new files to add")
            sys.exit(0)
        print(f"Adding {len(entries)} new files to tracker")

    # Generate content
    content = generate_tracker(args.skill, entries)

    if args.dry_run:
        print(content)
    else:
        output.write_text(content)
        print(f"Generated: {output}")
        print(f"  Files: {len(entries)}")
        print(f"  Total LOC: {sum(e.loc for e in entries):,}")


if __name__ == "__main__":
    main()
