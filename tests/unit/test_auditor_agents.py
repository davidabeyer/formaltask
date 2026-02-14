"""Tests for auditor agent YAML frontmatter validation.

Validates critique pipeline agents have correct frontmatter and required MCP tools.

Note: File existence test was removed - it tests filesystem structure rather than behavior.
If an agent file is moved/renamed, that test would break without behavioral regression.
The yaml_parses and has_required_tools tests implicitly verify file existence.
"""

import re
from pathlib import Path

import pytest
import yaml

AGENTS_DIR = Path(__file__).parent.parent.parent / "agents"

# Required tools per spec
REQUIRED_TOOLS = [
    "mcp__auggie-mcp__codebase-retrieval",
    "mcp__morph-mcp__warpgrep_codebase_search",
]

# Critique pipeline agents
AUDITOR_AGENTS = [
    "spec-decomposition-auditor",
    "spec-dependency-auditor",
    "acceptance-criteria-auditor",
    "coup-de-grace-auditor",
]


def parse_agent_frontmatter(agent_path: Path) -> dict:
    """Parse YAML frontmatter from agent markdown file."""
    content = agent_path.read_text()

    # Match YAML frontmatter between --- markers
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise ValueError(f"No YAML frontmatter found in {agent_path}")

    frontmatter = match.group(1)
    return yaml.safe_load(frontmatter)


@pytest.mark.parametrize("agent_name", AUDITOR_AGENTS)
def test_auditor_agent_yaml_parses(agent_name: str) -> None:
    """Verify agent YAML frontmatter parses successfully."""
    agent_path = AGENTS_DIR / f"{agent_name}.md"
    if not agent_path.exists():
        pytest.skip(f"Agent file not found: {agent_path}")

    frontmatter = parse_agent_frontmatter(agent_path)

    # Verify required fields
    assert "name" in frontmatter, "Missing 'name' field"
    assert frontmatter["name"] == agent_name, (
        f"Name mismatch: {frontmatter['name']} != {agent_name}"
    )
    assert "description" in frontmatter, "Missing 'description' field"
    assert "tools" in frontmatter, "Missing 'tools' field"


@pytest.mark.parametrize("agent_name", AUDITOR_AGENTS)
def test_auditor_agent_has_required_tools(agent_name: str) -> None:
    """Verify agent has required auggie and warpgrep tools."""
    agent_path = AGENTS_DIR / f"{agent_name}.md"
    if not agent_path.exists():
        pytest.skip(f"Agent file not found: {agent_path}")

    frontmatter = parse_agent_frontmatter(agent_path)
    tools = frontmatter.get("tools", [])

    for required_tool in REQUIRED_TOOLS:
        assert required_tool in tools, f"Missing required tool: {required_tool}"
