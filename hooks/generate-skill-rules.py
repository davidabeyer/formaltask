#!/usr/bin/env python3
"""
Dynamic Skill Rules Generator

Scans skills directories and generates skill-rules.json from SKILL.md frontmatter.
Run this whenever skills are added/modified to regenerate the rules file.

Usage:
    python3 generate-skill-rules.py [--output PATH]
"""

import json
import re
import sys
from pathlib import Path

from formaltask.paths import get_claude_home

# Directories to scan for skills (Task #2483: use path_config for configurability)
SKILL_DIRS = [
    get_claude_home() / "skills",
]

# Output path (Task #2483: use path_config for configurability)
DEFAULT_OUTPUT = get_claude_home() / "hooks" / "skill-rules.json"

# Keywords to extract from descriptions for trigger generation
TRIGGER_KEYWORDS = {
    # Action verbs
    "debug": ["debug", "fix", "error", "bug", "issue", "broken", "failing"],
    "test": ["test", "tdd", "spec", "unittest", "pytest", "testing"],
    "review": ["review", "audit", "check", "analyze", "examine"],
    "plan": ["plan", "design", "architect", "implement", "feature"],
    "research": ["research", "investigate", "explore", "compare", "evaluate"],
    "create": ["create", "build", "generate", "new", "add"],
    "simplify": ["simplify", "refactor", "clean", "reduce", "complexity"],
    "document": ["document", "docs", "readme", "documentation"],
    "critique": ["critique", "feedback", "gaps", "blind spots"],
    # Domain terms
    "hook": ["hook", "automation", "pretooluse", "posttooluse"],
    "skill": ["skill", "skills"],
    "agent": ["agent", "subagent"],
    "mcp": ["mcp", "server", "tool"],
    "cli": ["cli", "command", "terminal"],
    "workflow": ["workflow", "lifecycle", "pipeline", "process"],
    "security": ["security", "vulnerability", "owasp", "injection"],
    "performance": ["performance", "optimize", "slow", "fast"],
}


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    frontmatter = {}
    yaml_content = match.group(1)

    # Simple YAML parsing (name and description)
    for line in yaml_content.split("\n"):
        if line.startswith("name:"):
            frontmatter["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            # Handle multi-line description
            desc = line.split(":", 1)[1].strip()
            if desc.startswith(">"):
                desc = ""
            frontmatter["description"] = desc

    # Handle multi-line description
    if "description" in frontmatter and not frontmatter["description"]:
        # Find description block
        desc_match = re.search(r"description:\s*>-?\s*\n((?:\s+.+\n?)+)", yaml_content)
        if desc_match:
            frontmatter["description"] = " ".join(
                line.strip() for line in desc_match.group(1).split("\n") if line.strip()
            )

    return frontmatter


def generate_triggers(name: str, description: str) -> dict:
    """Generate trigger patterns from skill name and description."""
    triggers = {
        "keywords": [],
        "keywordPatterns": [],
        "intentPatterns": [],
    }

    desc_lower = description.lower()
    name_lower = name.lower()

    # Add skill name variations as keywords
    triggers["keywords"].append(name)
    if "-" in name:
        triggers["keywords"].append(name.replace("-", " "))

    # Find matching keyword categories
    for _, keywords in TRIGGER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower or keyword in name_lower:
                triggers["keywords"].extend([k for k in keywords if k not in triggers["keywords"]])
                break

    # Remove duplicates and limit
    triggers["keywords"] = list(dict.fromkeys(triggers["keywords"]))[:8]

    # Generate keyword patterns
    if triggers["keywords"]:
        for kw in triggers["keywords"][:3]:
            triggers["keywordPatterns"].append(f"\\b{kw}\\b")

    # Generate intent patterns based on description
    if any(word in desc_lower for word in ["must be used", "use when", "activates when"]):
        # Extract activation conditions
        intent_match = re.search(
            r"(?:must be used|use when|activates? (?:on|when))\s+([^.]+)", desc_lower
        )
        if intent_match:
            condition = intent_match.group(1).strip()
            # Create intent pattern from condition
            words = [w for w in condition.split() if len(w) > 3][:4]
            if words:
                triggers["intentPatterns"].append(
                    f"(?:{'|'.join(words[:2])}).*(?:{'|'.join(words[2:4]) if len(words) > 2 else words[0]})"
                )

    return triggers


def calculate_priority(name: str, description: str) -> int:
    """Calculate skill priority based on content."""
    desc_lower = description.lower()

    # Higher priority for debugging, testing, planning
    if any(word in desc_lower for word in ["must be used", "critical", "always"]):
        return 9
    if any(word in name for word in ["debug", "test", "plan", "review"]):
        return 8
    if any(word in name for word in ["audit", "validate", "verify"]):
        return 7
    if any(word in name for word in ["research", "explore", "analyze"]):
        return 6

    return 5


def scan_skills() -> dict:
    """Scan skill directories and build rules."""
    skills = {}

    for skill_dir in SKILL_DIRS:
        if not skill_dir.exists():
            continue

        for skill_path in skill_dir.iterdir():
            if not skill_path.is_dir():
                continue

            skill_file = skill_path / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                content = skill_file.read_text()
                frontmatter = extract_frontmatter(content)

                name = frontmatter.get("name", skill_path.name)
                description = frontmatter.get("description", "")

                if not description:
                    continue

                skills[name] = {
                    "description": description,
                    "priority": calculate_priority(name, description),
                    "triggers": generate_triggers(name, description),
                }
            except Exception as e:
                print(f"Warning: Failed to process {skill_file}: {e}", file=sys.stderr)

    return skills


def generate_rules() -> dict:
    """Generate complete skill rules configuration."""
    skills = scan_skills()

    return {
        "$schema": "./skill-rules.schema.json",
        "version": "2.0-dynamic",
        "generated": True,
        "config": {"minConfidenceScore": 3, "showMatchReasons": True, "maxSkillsToShow": 5},
        "scoring": {
            "keyword": 2,
            "keywordPattern": 3,
            "pathPattern": 4,
            "directoryMatch": 5,
            "intentPattern": 4,
            "contentPattern": 3,
            "contextPattern": 2,
        },
        "directoryMappings": {
            "hooks/": "hooks-automation",
            "hooks/lib/": "hooks-automation",
            "hooks/cli/": "developing-cli-commands",
            "skills/": "skill-creator",
            ".claude/hooks/": "hooks-automation",
            ".claude/agents/": "agent-creator",
            "plans/": "expert-planner",
            "plans/epics/": "expert-planner",
            "plans/PRPs/": "expert-planner",
        },
        "skills": skills,
    }


def main():
    output_path = DEFAULT_OUTPUT

    if len(sys.argv) > 2 and sys.argv[1] == "--output":
        output_path = Path(sys.argv[2])

    rules = generate_rules()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rules, indent=2))

    print(f"Generated {len(rules['skills'])} skill rules to {output_path}")


if __name__ == "__main__":
    main()
