# Worktree Worker Scripts

> See also: `skills/_references/orchestration.md` for shared orchestration patterns.

## Handoff Template

```markdown
## Worker Assignment
worker_id: {uuid[:8]}
output_path: {run_dir}/outputs/{worker-id}.md
complete_marker: {run_dir}/outputs/{worker-id}.complete

## Files
- {file1}
- {file2}

## Test Codex (9 Patterns)
{FULL content of test-codex.md - workers are context-blind}

## Instructions
1. Read ALL assigned files completely
2. Score each against 9 patterns with evidence
3. Apply Beck's razor to every test function
4. Write findings to output_path
5. Touch complete_marker when done
```

## Spawn Workers

```bash
for handoff in {run_dir}/handoffs/*.md; do
    worker_id=$(basename "$handoff" .md)
    worktree_path="$HOME/.claude/worktrees/audit-${worker_id}"

    git worktree add --detach "$worktree_path" HEAD

    tmux new-session -d \
        -s "audit-${worker_id}" \
        -c "$worktree_path" \
        -e "PROJECT_ROOT=$(git rev-parse --show-toplevel)" \
        -e "HANDOFF_PATH=${handoff}" \
        -e "OUTPUT_PATH=${run_dir}/outputs/${worker_id}.md" \
        bash --norc --noprofile

    tmux send-keys -t "audit-${worker_id}" \
        "export HANDOFF_PATH='${handoff}' && export OUTPUT_PATH='${run_dir}/outputs/${worker_id}.md' && claude --permission-mode dontAsk -p '/test-audit-worker'" \
        Enter
done
```

## Poll Completion

```bash
while true; do
    complete_count=$(ls -1 {run_dir}/outputs/*.complete 2>/dev/null | wc -l)
    [ "$complete_count" -eq "$expected_count" ] && break
    sleep 30
done
```

## Orchestrator Re-verification (Phase 6)

After workers complete, aggregate all P0/P1 claims and re-verify with fresh context:

```python
# Collect all P0/P1 DELETE/SIMPLIFY claims from worker outputs
claims = []
for output in Path(f"{run_dir}/outputs").glob("*.md"):
    # Extract from "### DELETE List" and "### Simplify List" tables
    # Format: {"file": "test_foo.py:42", "test": "test_bar", "action": "DELETE", "reason": "..."}

# Spawn claim-verifier with aggregated claims
Task(
    subagent_type="claim-verifier",
    description="Re-verify aggregated P0/P1 claims",
    prompt=f"""Verify these DELETE/SIMPLIFY claims from test audit workers.

For each claim, check:
1. Does another test actually cover this behavior?
2. Would deleting this let a real bug slip through?

Claims to verify:
{json.dumps(claims, indent=2)}

Output format per claim:
| Claim | Worker Said | Your Verdict | Evidence |
"""
)
```

Workers may miss cross-file coverage. Re-verification catches false positives before synthesis.

## Cleanup

```bash
for worktree in ~/.claude/worktrees/audit-*; do
    tmux kill-session -t "$(basename "$worktree")" 2>/dev/null || true
    git worktree remove --force "$worktree" 2>/dev/null || true
done
```

## Synthesis Template

```markdown
## Test Audit: {module_batch}
**Files:** {count} | **Tests:** {count} | **Avg Score:** X/9

### Batch Summary
| File | Tests | Score | P0 | P1 | P2 | Verdict |
|------|-------|-------|----|----|----|---------|

### Verification Results (Aggregated)
| Worker | Claim | Worker Said | Orchestrator Re-verified | Final |
|--------|-------|-------------|-------------------------|-------|

### Delete List (Beck's Razor)
| File:Line | Test | Why Delete | Verified? |
|-----------|------|------------|-----------|

### Simplify List
| File:Line | Test | Problem | Verified? |
|-----------|------|---------|-----------|

### Keep List
| File:Line | Test | Why Essential |
|-----------|------|---------------|
```
