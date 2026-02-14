# Anchor Comment Conventions

## For Major Patterns

Add anchor comments for reusable, significant patterns:

```markdown
<!-- PATTERN-NAME -->
### Pattern Title

**Purpose**: Brief description of what this pattern does

**Usage**: When to use this pattern

**Implementation**:
- Key implementation details
- File references with line numbers

**Example**:
```language
# Code example
```

**See**: Related patterns or files
```

## For Command Reference

Update Common Commands section with executable examples:

```markdown
## Common Commands

```bash
# Command description
command-name --arg value

# Example use case
actual-example-command
```
```

## For Project Rules

Add to Project-Specific Rules with numbered list:

```markdown
## Project-Specific Rules

1. **Rule description** - Implementation requirement
2. **Next rule** - Rationale and consequences
```

## Referencing Anchors in Code

When a pattern has an anchor comment, reference it in related code:

```python
"""Module implementing X.

Implements <!-- PATTERN-NAME --> from CLAUDE.md:section.
See CLAUDE.md for usage and examples.
"""
```

This creates bidirectional discoverability:
- Documentation -> Code: References show where pattern is used
- Code -> Documentation: Docstrings point to detailed guidance

## Naming Conventions

- **Choose anchor name**: Use UPPERCASE-WITH-HYPHENS
  - Good: `BACKGROUND-WORKERS`, `METADATA-SIDECAR`
  - Bad: `background_workers`, `MetadataSidecar`

## Best Practices

- **Use sparingly**: Only for major, reusable patterns
- **Choose clear names**: Should describe the pattern clearly
- **Reference consistently**: Always use same anchor in related code
- **Maintain index**: Update anchor cross-reference if it exists
