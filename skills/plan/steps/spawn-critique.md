---
consumes: [plan-file]
produces: [critique-verdict]
optional: true
---
## Phase 7: Spawn Critique

**MANDATORY. No plan exits without critique.**

**BLOCKING GATE:** Plan must be written to disk (Phase 6 complete).

After plan is written, spawn /critique in background and check on it.

```bash
# Sanitize project name (alphanumeric, hyphens, underscores only)
safe_project=$(echo "$project" | tr -cd 'a-zA-Z0-9_-')
[ -z "$safe_project" ] && { echo "Invalid project name"; exit 1; }

# Create isolated worktree in persistent location
mkdir -p "$HOME/.claude/worktrees"
worktree_path="$HOME/.claude/worktrees/critique-${safe_project}"

# Only create worktree if doesn't exist
if [ ! -d "$worktree_path" ]; then
    git worktree add --detach "$worktree_path" HEAD || { echo "Worktree creation failed"; exit 1; }
fi

# Spawn critique in tmux session (NON-BLOCKING)
# Pattern: launch bash first, then send claude command via send-keys
session_id="critique-${safe_project}"
tmux kill-session -t "$session_id" 2>/dev/null || true

tmux new-session -d \
    -s "$session_id" \
    -c "$worktree_path" \
    bash --norc --noprofile

tmux send-keys -t "$session_id" \
    "claude --permission-mode dontAsk -p '/critique ${safe_project}'" \
    Enter

echo "Critique spawned in session: $session_id"
echo "Worktree: $worktree_path"
echo "Attach: tmux attach -t $session_id"
```

**DO NOT block waiting for critique.** Instead:

1. Tell user: "Critique running in `tmux attach -t critique-{project}`"
2. Check if critique produced output: `ls .plans/critique-outputs/{project}-*/`
3. If output exists, read verdict and route
4. If no output yet, ask user: "Critique still running. Wait, check manually, or proceed?"

**Checking critique status:**
```bash
# Check if session still running
tmux has-session -t "critique-${safe_project}" 2>/dev/null && echo "Still running" || echo "Finished"

# Check for output
ls -la .plans/critique-outputs/${safe_project}-*/ 2>/dev/null || echo "No output yet"
```

**Verdict routing:**

| Verdict | Action |
|---------|--------|
| APPROVED | Proceed to `/decompose {project}` |
| FIX_AND_SHIP | Run `/revise {project}`, then re-critique |
| REVISE | Return to relevant phase, fix, re-critique |
| (no output yet) | Ask user: wait, check manually, or proceed with risk |

**EXIT CRITERIA:** Critique verdict received OR user explicitly proceeds without.
