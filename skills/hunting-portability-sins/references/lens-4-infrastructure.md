# Lens 4: Infrastructure Coupling

Find dependencies on specific infrastructure configurations that may not exist elsewhere.

## Search Patterns

```python
# tmux usage
Grep(pattern="tmux|\\$TMUX|TMUX_PANE", output_mode="content")

# SQLite configuration specifics
Grep(pattern="PRAGMA|WAL|journal_mode|busy_timeout|foreign_keys", output_mode="content")

# Git hook references
Grep(pattern="core\\.hooksPath|\\.githooks|pre-commit|post-commit", output_mode="content")

# Git worktree assumptions
Grep(pattern="git worktree|--work-tree|GIT_WORK_TREE", output_mode="content")

# Systemd/service assumptions
Grep(pattern="systemctl|systemd|/etc/systemd", output_mode="content")
```

## Blocker Criteria

| Pattern | Severity | Rationale |
|---------|----------|-----------|
| tmux 3.2+ features (`-e` flag) | Warning | Older tmux versions fail |
| WAL mode without fallback | Warning | May not work on all SQLite builds |
| Auto git hook setup required | Warning | User may not want hooks |
| Worktree-specific paths | Blocker | Breaks in normal git repos |
| Hardcoded socket paths | Blocker | User-specific paths |

## tmux Version Compatibility

```python
# tmux 3.2+ feature (env passing with -e)
tmux new-session -d -e "TASK_ID=123"  # Fails on tmux < 3.2

# Portable alternative
tmux new-session -d \; set-environment TASK_ID 123
# Or: Detect version and fallback
```

## SQLite Configuration

```python
# Potentially problematic
conn.execute("PRAGMA journal_mode=WAL")  # May fail on network filesystems

# More portable
journal_mode = os.environ.get("SQLITE_JOURNAL_MODE", "DELETE")
if journal_mode == "WAL":
    # Check if WAL is supported
    result = conn.execute("PRAGMA journal_mode=WAL").fetchone()
    if result[0] != "wal":
        conn.execute("PRAGMA journal_mode=DELETE")
```

## Git Hook Setup

```python
# Problematic: Assumes hooks are configured
def run_pre_commit():
    # Assumes .githooks/ exists and is configured
    subprocess.run([".githooks/pre-commit"])

# Better: Check and guide
def ensure_hooks():
    hooks_path = subprocess.run(
        ["git", "config", "core.hooksPath"],
        capture_output=True, text=True
    ).stdout.strip()

    if hooks_path != ".githooks":
        print("Configure hooks: git config core.hooksPath .githooks")
```

## Acceptable Patterns

```python
# Good: Version detection
def get_tmux_version():
    result = subprocess.run(["tmux", "-V"], capture_output=True, text=True)
    # "tmux 3.2" -> (3, 2)
    match = re.search(r"(\d+)\.(\d+)", result.stdout)
    return tuple(map(int, match.groups())) if match else (0, 0)

TMUX_VERSION = get_tmux_version()
USE_TMUX_ENV = TMUX_VERSION >= (3, 2)

# Good: Fallback detection
def detect_task_id():
    """Get task ID with multiple detection methods."""
    if task_id := os.environ.get("TASK_ID"):
        return task_id
    if tmux_pane := os.environ.get("TMUX_PANE"):
        return extract_from_pane(tmux_pane)
    return extract_from_worktree_path()
```

## Output Fields

```json
{
  "id": "L4-001",
  "severity": "warning",
  "category": "tmux_version",
  "feature": "tmux -e flag for env passing",
  "location": {"file": "hooks/lib/worker.py", "line": 156},
  "minimum_version": "3.2",
  "fallback_exists": true,
  "fallback_location": {"file": "hooks/lib/worker.py", "line": 162},
  "fix": "Already has fallback, but document tmux version requirement"
}
```
