# Lens 6: File System Assumptions

Find assumptions about directory structure, permissions, and file system features.

## Search Patterns

```python
# Directory creation
Grep(pattern="os\\.makedirs|mkdir|Path.*mkdir", output_mode="content")

# File permission checks
Grep(pattern="os\\.access|os\\.chmod|stat\\.S_", output_mode="content")

# Symlink operations
Grep(pattern="os\\.symlink|os\\.readlink|is_symlink", output_mode="content")

# Path existence checks
Grep(pattern="os\\.path\\.exists|Path.*exists", output_mode="content")

# Hardcoded directory expectations
Grep(pattern='(mkdir|makedirs).*["\'](\\.|~|/)', output_mode="content")
```

## Blocker Criteria

| Pattern | Severity | Rationale |
|---------|----------|-----------|
| Expected dir not created on demand | Blocker | FileNotFoundError |
| Write to user-specific location | Blocker | Path won't exist |
| Symlink without Windows check | Warning | Symlinks need admin on Windows |
| Case-sensitive path assumptions | Warning | macOS/Windows case-insensitive |
| Hardcoded `/tmp/` reliance | Note | Works usually but not universal |

## Common Assumptions

### Directory Must Exist

```python
# Problematic: Assumes directory exists
with open("~/.claude/cache/data.json", "w") as f:
    json.dump(data, f)

# Better: Create on demand
cache_dir = Path.home() / ".claude" / "cache"
cache_dir.mkdir(parents=True, exist_ok=True)
with open(cache_dir / "data.json", "w") as f:
    json.dump(data, f)
```

### Permission Requirements

```python
# Problematic: Assumes write permission
def save_config(config):
    with open("/etc/myapp/config.json", "w") as f:
        json.dump(config, f)

# Better: User-writable location
def get_config_dir():
    if xdg := os.environ.get("XDG_CONFIG_HOME"):
        return Path(xdg) / "myapp"
    return Path.home() / ".config" / "myapp"
```

### Symlink Portability

```python
# Problematic: Assumes symlinks work
os.symlink(target, link_name)

# Better: Check and fallback
def create_link(target, link_name):
    try:
        os.symlink(target, link_name)
    except OSError:
        # Windows without admin, or other restriction
        shutil.copy2(target, link_name)
```

## XDG Base Directory Spec

Use XDG directories for portability:

| Purpose | XDG Variable | Fallback |
|---------|--------------|----------|
| Config | `XDG_CONFIG_HOME` | `~/.config` |
| Data | `XDG_DATA_HOME` | `~/.local/share` |
| Cache | `XDG_CACHE_HOME` | `~/.cache` |
| State | `XDG_STATE_HOME` | `~/.local/state` |

```python
def get_data_dir():
    if xdg := os.environ.get("XDG_DATA_HOME"):
        return Path(xdg) / "myapp"
    return Path.home() / ".local" / "share" / "myapp"
```

## Acceptable Patterns

```python
# Good: On-demand creation
def ensure_cache_dir():
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    app_cache = cache / "myapp"
    app_cache.mkdir(parents=True, exist_ok=True)
    return app_cache

# Good: Temp directory for ephemeral files
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    work_file = Path(tmpdir) / "work.json"

# Good: Check before assuming
def get_working_dir():
    for candidate in [
        Path(os.environ.get("PROJECT_ROOT", "")),
        Path.cwd(),
        Path(__file__).parent.parent,
    ]:
        if candidate.exists() and (candidate / ".claude").exists():
            return candidate
    raise ConfigError("Could not determine project root")
```

## Output Fields

```json
{
  "id": "L6-001",
  "severity": "blocker",
  "category": "directory_assumption",
  "path": ".claude/cache/",
  "location": {"file": "hooks/lib/cache.py", "line": 23},
  "created_on_demand": false,
  "existence_checked": false,
  "fix": "Add mkdir(parents=True, exist_ok=True) before first write"
}
```
