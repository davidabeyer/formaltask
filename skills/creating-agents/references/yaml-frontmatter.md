# YAML Frontmatter Reference

## Format

```yaml
---
name: agent-name                    # Required: kebab-case identifier
description: >                      # Required: WHEN to invoke (not just WHAT)
  MUST BE USED when [specific scenario].
  Use PROACTIVELY when [trigger condition].
  Examples - "[user says X]" → Launch to [do Y]
tools:                              # Recommended: Restrict to minimum needed
  - Read
  - Grep
  - Glob
model: sonnet                       # Optional: sonnet|opus|haiku|inherit
---
```

## Required Fields

| Field | Purpose | Quality Criteria |
|-------|---------|------------------|
| `name` | Agent identifier | Lowercase with hyphens, descriptive |
| `description` | When to invoke | Must explain WHEN, not just WHAT. Include trigger examples |

## Optional Fields

| Field | Purpose | Values |
|-------|---------|--------|
| `tools` | Restrict available tools | Array of tool names |
| `model` | Model selection | `sonnet` (balanced), `opus` (complex), `haiku` (fast), `inherit` |
| `color` | Visual categorization | blue, green, red, purple, orange |
| `field` | Domain area | testing, security, quality, research, debugging |
| `expertise` | Complexity level | beginner, intermediate, expert |
