# formaltask/git/

Git and GitHub integration for FormalTask. Worktree management, PR queries, and status utilities.

## Quick Start

```python
from formaltask.git.worktree import cleanup_stale_worktrees
from formaltask.git.github import get_prs_for_tasks

# Clean up stale worktrees before spawning
cleanup_stale_worktrees(db_path)

# Get PRs for task branches
prs = get_prs_for_tasks([42, 43, 44])
for task_id, pr in prs.items():
    print(f"Task {task_id}: PR #{pr.number} ({pr.state})")
```

## Worktree Cleanup

Safe worktree deletion with 5 safety checks:

```python
from formaltask.git.worktree import check_worktree_safety, cleanup_single_worktree

# Check if worktree is safe to delete
result = check_worktree_safety("/path/to/worktree")
# Returns: {"safe": bool, "reason": str, "checks": {...}}

if result["safe"]:
    cleanup_single_worktree("/path/to/worktree")
```

### Safety Checks

A worktree is only deleted if **ALL** checks pass:

| Check | Blocks If |
|-------|-----------|
| `clean` | Has uncommitted changes |
| `no_tmux` | Active tmux session exists |
| `merged_pr` | Has unmerged PR to master |
| `no_open_pr` | Has open PR |
| `no_local_commits` | Has unpushed local commits |

```python
from formaltask.git.worktree import cleanup_stale_worktrees

# Batch cleanup during spawn
cleanup_stale_worktrees(db_path)  # Called by spawner
```

## GitHub PR Queries

Batch PR lookup with 300s TTL cache:

```python
from formaltask.git.github import get_prs_for_tasks, get_pr_for_task, PRInfo

# Batch query (cached)
prs: dict[int, PRInfo] = get_prs_for_tasks([42, 43, 44])

# Single task lookup
pr = get_pr_for_task(42)
if pr:
    print(f"PR #{pr.number}: {pr.state} (merged={pr.merged})")
```

### PRInfo

```python
@dataclass
class PRInfo:
    number: int                              # PR number
    state: Literal["OPEN", "CLOSED", "MERGED"]
    merged: bool
```

### Fail-Open Behavior

All GitHub operations fail-open (return empty dict on error):
- Timeout after 30s
- `gh` CLI not found
- Invalid JSON response
- Network errors

## Git Status Utilities

```python
from formaltask.git.status import (
    get_reviews_status,        # Get review status for worktree
    get_commits_ahead_of_main, # Count commits ahead of main
    get_finding_counts,        # Count findings by priority
)

# Check how far ahead of main
count = get_commits_ahead_of_main(worktree_path)

# Get reviews status
status = get_reviews_status(worktree_path)
```

## Git Utilities

```python
from formaltask.git.utils import (
    get_head_sha,         # Get HEAD commit SHA
    commit_exists,        # Check if commit exists
    is_ancestor,          # Check if commit is ancestor
    fetch_remote,         # Fetch from remote
    get_default_branch,   # Get default branch (main/master)
    find_task_in_commits, # Search commits for task ID
    find_pr_in_commits,   # Search commits for PR number
)

# Get current HEAD
sha = get_head_sha(worktree_path)

# Check ancestry
if is_ancestor(base_sha, head_sha, cwd=worktree_path):
    print("head is descendant of base")

# Get default branch
branch = get_default_branch()  # "main" or "master"
```

## Key Files

| File | Purpose |
|------|---------|
| `worktree.py` | Worktree cleanup with 5 safety checks |
| `github.py` | Batch PR query with TTL cache |
| `utils.py` | Git utilities: ancestry, commit search |
| `status.py` | Reviews status, commits ahead, findings |
| `pr.py` | PR creation utilities |

## Common Gotchas

| Issue | Solution |
|-------|----------|
| Worktree not cleaned up | Check `check_worktree_safety()` — likely uncommitted changes |
| PR query returns empty | GitHub API may be down — all queries fail-open |
| Stale PR cache | Cache TTL is 300s — use `clear_cache()` to force refresh |
| "gh CLI not found" | Install GitHub CLI: `brew install gh` |
| Timeout on PR query | Network issue — 30s timeout is hardcoded |

## See Also

- `formaltask/workers/spawner.py` — Calls `cleanup_stale_worktrees()`
- `formaltask/tasks/spawnability.py` — Uses PR status for spawn decisions
- `formaltask/core/completion_state.py` — Uses PR info for completion checks
