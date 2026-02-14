# Lens 2: Environment Variables

Find required environment variables that lack defaults, documentation, or graceful failure.

## Search Patterns

```python
# Direct dict access (no default)
Grep(pattern='os\\.environ\\["(\\w+)"\\]', output_mode="content")

# getenv without default
Grep(pattern='os\\.getenv\\("(\\w+)"\\)(?!,)', output_mode="content")

# getenv with None check after
Grep(pattern='os\\.getenv.*\\nif.*is None.*raise', multiline=True, output_mode="content")

# Shell variable expansion
Grep(pattern='\\$\\{?(\\w+)\\}?', glob="**/*.sh", output_mode="content")
```

## Blocker Criteria

| Pattern | Severity | Rationale |
|---------|----------|-----------|
| `os.environ["VAR"]` undocumented | Blocker | KeyError with no guidance |
| API key required at import | Blocker | Fails before user can configure |
| Required var not in README | Blocker | User can't discover requirement |
| `getenv()` with None causing crash | Warning | Delayed failure is confusing |
| Optional var with unclear purpose | Note | Works but confuses users |

## Environment Variable Audit Checklist

For each env var found:
1. Is it documented in README/CLAUDE.md?
2. Does it have a sensible default?
3. Does failure provide clear error message?
4. Is there a `.env.example` file?

## Acceptable Patterns

```python
# Good: Default provided
api_key = os.environ.get("API_KEY", "")

# Good: Explicit requirement with message
api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    raise ConfigError("Set OPENROUTER_API_KEY in environment")

# Good: Optional with documentation
DEBUG = os.environ.get("DEBUG", "").lower() == "true"

# Good: Documented in code
# Required: PROJECT_ROOT - base directory for all paths
project_root = os.environ["PROJECT_ROOT"]
```

## Documentation Check

Verify each required env var appears in:
- README.md "Environment Variables" section
- CLAUDE.md environment table
- `.env.example` (if present)
- Error messages when missing

## Output Fields

```json
{
  "id": "L2-001",
  "severity": "blocker",
  "category": "undocumented_required",
  "variable": "OPENROUTER_API_KEY",
  "access_pattern": "os.environ[\"OPENROUTER_API_KEY\"]",
  "location": {"file": "hooks/lib/llm.py", "line": 12},
  "documented": false,
  "has_default": false,
  "error_message": "KeyError: 'OPENROUTER_API_KEY'",
  "fix": "Add to README.md env vars table, use getenv with helpful error"
}
```
