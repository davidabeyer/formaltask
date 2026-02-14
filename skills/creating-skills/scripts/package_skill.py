#!/usr/bin/env python3
"""
Skill Packager - Creates a distributable zip file of a skill folder

Usage:
    python utils/package_skill.py <path/to/skill-folder> [output-directory]
    python utils/package_skill.py <path/to/skill-folder> --install

Example:
    python utils/package_skill.py skills/public/my-skill
    python utils/package_skill.py skills/public/my-skill ./dist
    python utils/package_skill.py skills/public/my-skill --install  # Auto-install to ~/.claude/skills/
"""

import shutil
import sys
import zipfile
from pathlib import Path

from quick_validate import validate_skill


def package_skill(skill_path, output_dir=None, install=False):
    """
    Validate a skill folder (zipping disabled per user request).

    Args:
        skill_path: Path to the skill folder
        output_dir: Ignored (kept for compatibility)
        install: Ignored (kept for compatibility)

    Returns:
        Path to skill if valid, or None if error
    """
    skill_path = Path(skill_path).resolve()

    # Validate skill folder exists
    if not skill_path.exists():
        print(f"❌ Error: Skill folder not found: {skill_path}")
        return None

    if not skill_path.is_dir():
        print(f"❌ Error: Path is not a directory: {skill_path}")
        return None

    # Validate SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        print(f"❌ Error: SKILL.md not found in {skill_path}")
        return None

    # Run validation
    print("🔍 Validating skill...")
    valid, message = validate_skill(skill_path)
    if not valid:
        print(f"❌ Validation failed: {message}")
        print("   Please fix the validation errors.")
        return None
    print(f"✅ {message}\n")

    # ZIPPING DISABLED - Skills are used directly as directories
    print(f"✅ Skill validated successfully: {skill_path}")
    print(f"📁 Skills are used as directories (no ZIP needed)")
    print(f"💡 Skill is ready to use in Claude Code!")

    return skill_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python utils/package_skill.py <path/to/skill-folder>")
        print("\nExample:")
        print("  python utils/package_skill.py skills/public/my-skill")
        print("\nNote: This validates the skill structure (zipping disabled)")
        sys.exit(1)

    skill_path = sys.argv[1]

    print(f"🔍 Validating skill: {skill_path}\n")

    result = package_skill(skill_path)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
