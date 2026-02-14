# Lens 8: Documentation Gaps

Find missing documentation that would leave users unable to set up or use the project.

## Search Patterns

```python
# README existence and content
Read("README.md")
Grep(pattern="## (Installation|Setup|Getting Started|Prerequisites)", path="README.md")

# Environment variable documentation
Grep(pattern="\\| .* \\| .* \\| .* \\|", path="README.md")  # Tables
Grep(pattern="export \\w+=|\\$\\w+", path="README.md")

# CLAUDE.md requirements section
Grep(pattern="## (Environment|Prerequisites|Setup)", path="CLAUDE.md")
```

## Documentation Checklist

### README.md Must Have

| Section | Required | Purpose |
|---------|----------|---------|
| Project description | Yes | What it does |
| Installation | Yes | How to get it working |
| Prerequisites | Yes | What users need first |
| Environment variables | If any | All required env vars |
| Quick start | Yes | Minimal example |
| Configuration | If any | How to configure |
| Troubleshooting | Recommended | Common issues |

### For Each Env Var

Must document:
- Name
- Purpose
- Required/Optional
- Default value (if optional)
- Where to get it (for API keys)

### For Each Dependency

Must document:
- What it is
- Why it's needed
- How to install
- Version requirements

## Blocker Criteria

| Gap | Severity | Rationale |
|-----|----------|-----------|
| No installation instructions | Blocker | Users can't start |
| Required env var undocumented | Blocker | Cryptic KeyError |
| No prerequisites list | Warning | Users discover deps by failing |
| No troubleshooting section | Note | Users stuck on common issues |
| Outdated documentation | Warning | Wrong instructions worse than none |

## Implicit Knowledge Audit

Check for assumptions that aren't documented:

```python
# Search for "obvious" requirements that may not be
Grep(pattern="python3|pip|git|npm|node", output_mode="content")  # Runtime requirements
Grep(pattern="pytest|ruff|mypy", output_mode="content")  # Dev requirements
Grep(pattern="tmux|sqlite3", output_mode="content")  # Tool requirements
```

For each found: Is it in README prerequisites?

## Documentation Quality Checklist

For existing docs, verify:

1. **Accuracy** - Do commands actually work?
2. **Completeness** - All features documented?
3. **Currency** - Matches current code?
4. **Findability** - Can users find what they need?
5. **Examples** - Working code samples?

## Acceptable Documentation

```markdown
# MyProject

## Prerequisites

- Python 3.11+
- Git
- tmux 3.2+ (optional, for background workers)

## Installation

```bash
git clone https://github.com/user/myproject
cd myproject
pip install -e .
```

## Configuration

Copy the example config:
```bash
cp config.example.json ~/.config/myproject/config.json
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Yes | - | API key from openrouter.ai |
| `PROJECT_ROOT` | No | Current dir | Base directory for paths |
| `DEBUG` | No | `false` | Enable debug logging |

## Quick Start

```bash
export OPENROUTER_API_KEY="your-key-here"
python -m myproject.cli --help
```

## Troubleshooting

### "KeyError: OPENROUTER_API_KEY"
Set the environment variable: `export OPENROUTER_API_KEY=...`

### Database locked errors
Another process may be using the database. Check for running workers.
```

## Output Fields

```json
{
  "id": "L8-001",
  "severity": "blocker",
  "category": "missing_section",
  "missing": "Environment Variables table",
  "location": {"file": "README.md"},
  "env_vars_found": ["OPENROUTER_API_KEY", "PROJECT_ROOT"],
  "env_vars_documented": 0,
  "fix": "Add Environment Variables section with table documenting all required vars"
}
```
