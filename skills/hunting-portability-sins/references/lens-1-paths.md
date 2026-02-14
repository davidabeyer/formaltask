# Lens 1: Path Hardcoding

Find hardcoded paths that assume specific user directories or machine configurations.

## Search Patterns

```python
# User home directory references
Grep(pattern="/home/\\w+|/Users/\\w+", output_mode="content")

# Claude-specific paths
Grep(pattern="~/.claude|\\.claude/", output_mode="content")

# Absolute paths in strings
Grep(pattern='["\']/(?:home|Users|var|opt|tmp)', output_mode="content")

# Path construction without PROJECT_ROOT
Grep(pattern='Path\\(["\'][^"\']*["\']\\)', glob="**/*.py", output_mode="content")
```

## Blocker Criteria

| Pattern | Severity | Rationale |
|---------|----------|-----------|
| `/home/{username}/` | Blocker | Immediate failure for other users |
| `/Users/{username}/` | Blocker | macOS-specific user path |
| `~/.claude/` without fallback | Blocker | Assumes Claude Code installation |
| Hardcoded database path | Blocker | File won't exist elsewhere |
| Relative path that assumes CWD | Warning | May fail if run from different directory |
| Hardcoded `/tmp/` without XDG | Note | Usually works but not portable |

## Acceptable Patterns

```python
# Good: Environment variable based
db_path = os.environ.get("DB_PATH", "./.claude/formaltask.db")

# Good: PROJECT_ROOT based
config_path = Path(os.environ["PROJECT_ROOT"]) / "config.json"

# Good: XDG compliant
cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

# Good: Relative to module
THIS_DIR = Path(__file__).parent
```

## Evidence Requirements

Each finding must include:
- Exact file:line location
- The hardcoded path string
- Where this path would fail
- Suggested fix pattern

## Output Fields

```json
{
  "id": "L1-001",
  "severity": "blocker",
  "category": "user_path",
  "path_found": "/home/user/cc/.claude/formaltask.db",
  "location": {"file": "hooks/lib/db.py", "line": 45},
  "breaks_on": "Any machine without /home/user directory",
  "fix_pattern": "Use PROJECT_ROOT or XDG_DATA_HOME"
}
```
