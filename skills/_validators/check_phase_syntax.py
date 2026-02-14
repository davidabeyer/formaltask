#!/usr/bin/env python3
"""Validate phase header syntax in skill files.

Catches malformed ## Phase N: headers before they break runtime extraction.

Usage:
    python3 check_phase_syntax.py                    # Check all skills
    python3 check_phase_syntax.py skill-name         # Check one skill
    python3 check_phase_syntax.py --staged           # Check git staged files (pre-commit)

Exit codes:
    0 = all valid
    1 = malformed headers found
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent

# Correct pattern
VALID_PHASE = re.compile(r"^## Phase \d+:\s*.+$")

# Suspicious patterns that look like phases but are wrong
MALFORMED_PATTERNS = [
    (r"^##Phase\s+\d+:\s*.+$", "missing space after ##"),
    (r"^###+ Phase\s+\d+:\s*.+$", "wrong heading level (use ##)"),
    (r"^## Step\s+\d+:\s*.+$", "use 'Phase' not 'Step'"),
    (r"^## Phase\s+\d+\s+[^:].+$", "missing colon after number"),
    (r"^## Phase\s+[A-Za-z]+:\s*.+$", "use digit not word"),
    (r"^##\s+Phase\s+\d+:\s*.+$", "extra space after ##"),
]


def check_skill(skill_path: Path) -> list[str]:
    """Check a skill file for malformed phase headers."""
    if not skill_path.exists():
        return []

    content = skill_path.read_text()
    errors = []

    for i, line in enumerate(content.split("\n"), 1):
        # Skip if it matches correct pattern
        if VALID_PHASE.match(line):
            continue

        # Check for malformed patterns
        for pattern, reason in MALFORMED_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                errors.append(f"  Line {i}: {line.strip()}")
                errors.append(f"    → {reason}")
                break

    return errors


def get_staged_skills() -> list[Path]:
    """Get skill files that are staged for commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = result.stdout.strip().split("\n")
        skills = []
        for f in files:
            if f and "skills/" in f and f.endswith("SKILL.md"):
                skills.append(Path(f))
        return skills
    except subprocess.CalledProcessError:
        return []


def main():
    args = sys.argv[1:]
    staged_only = "--staged" in args
    args = [a for a in args if not a.startswith("--")]

    if staged_only:
        skill_files = get_staged_skills()
        if not skill_files:
            sys.exit(0)  # No skills staged
    elif args:
        skill_files = [SKILLS_DIR / args[0] / "SKILL.md"]
    else:
        skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))

    all_errors = {}
    for skill_path in skill_files:
        errors = check_skill(skill_path)
        if errors:
            all_errors[skill_path] = errors

    if all_errors:
        print("Malformed phase headers found:", file=sys.stderr)
        print("Expected format: ## Phase N: Name", file=sys.stderr)
        print(file=sys.stderr)
        for path, errors in all_errors.items():
            print(f"{path}:", file=sys.stderr)
            for error in errors:
                print(error, file=sys.stderr)
            print(file=sys.stderr)
        sys.exit(1)

    if not staged_only:
        print(f"Checked {len(skill_files)} skill(s), all phase headers valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
