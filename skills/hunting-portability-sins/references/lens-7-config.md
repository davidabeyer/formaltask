# Lens 7: Configuration Portability

Find configuration systems that assume specific file locations, formats, or undocumented options.

## Search Patterns

```python
# Config file loading
Grep(pattern="json\\.load|yaml\\.load|toml\\.load|configparser", output_mode="content")

# Hardcoded config paths
Grep(pattern='(config|settings|preferences).*\\.json', output_mode="content")

# Config file existence checks
Grep(pattern='Path.*config.*exists|os\\.path\\.exists.*config', output_mode="content")

# Settings with hardcoded defaults
Grep(pattern='settings\\.get\\(|config\\[', output_mode="content")
```

## Blocker Criteria

| Pattern | Severity | Rationale |
|---------|----------|-----------|
| Required config file at fixed path | Blocker | File won't exist for new users |
| Config format undocumented | Warning | Users can't create valid config |
| No example/template config | Warning | Users must guess format |
| Required field with no default | Blocker | Fails without undocumented value |
| Config schema not validated | Note | Silent failures from typos |

## Configuration Discovery Chain

Good configuration systems search multiple locations:

```python
def find_config():
    """Find config file with fallback chain."""
    candidates = [
        Path(os.environ.get("MYAPP_CONFIG", "")),  # Explicit override
        Path.cwd() / "myapp.json",                  # Current directory
        Path.home() / ".config" / "myapp" / "config.json",  # XDG
        Path.home() / ".myapp.json",               # Home directory
        Path(__file__).parent / "default_config.json",  # Package default
    ]

    for path in candidates:
        if path and path.exists():
            return path

    return None  # Will use defaults
```

## Config Documentation Requirements

For each config option, document:
1. Name
2. Type
3. Default value
4. Description
5. Example value

```markdown
## Configuration

### Config File Location

Config is loaded from (in order):
1. `$MYAPP_CONFIG` environment variable
2. `./myapp.json` in current directory
3. `~/.config/myapp/config.json`

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `database_path` | string | `./.claude/formaltask.db` | SQLite database location |
| `log_level` | string | `INFO` | Logging verbosity |
| `timeout` | int | 30 | Request timeout in seconds |

### Example Config

```json
{
  "database_path": "/path/to/my/db.sqlite",
  "log_level": "DEBUG",
  "timeout": 60
}
```
```

## Acceptable Patterns

```python
# Good: Defaults for everything
DEFAULT_CONFIG = {
    "database_path": "./.claude/formaltask.db",
    "log_level": "INFO",
    "timeout": 30,
}

def load_config():
    config = DEFAULT_CONFIG.copy()
    config_file = find_config()
    if config_file:
        with open(config_file) as f:
            user_config = json.load(f)
            config.update(user_config)
    return config

# Good: Schema validation
from jsonschema import validate

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "database_path": {"type": "string"},
        "log_level": {"enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
    }
}

def load_config():
    config = json.load(config_file)
    validate(config, CONFIG_SCHEMA)
    return config

# Good: Example config shipped
def create_example_config():
    example = Path(__file__).parent / "config.example.json"
    if not example.exists():
        with open(example, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
```

## Output Fields

```json
{
  "id": "L7-001",
  "severity": "blocker",
  "category": "required_config",
  "config_path": "~/.claude/settings.json",
  "location": {"file": "hooks/lib/config.py", "line": 34},
  "fallback_chain": false,
  "defaults_provided": false,
  "example_exists": false,
  "schema_documented": false,
  "fix": "Add config discovery chain, defaults, and config.example.json"
}
```
