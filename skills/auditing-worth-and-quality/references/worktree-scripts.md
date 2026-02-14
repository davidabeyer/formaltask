# Worktree Worker Scripts

## Handoff Template

```markdown
## Target
file_path: {path}
loc: {line_count}
output_path: {run_dir}/outputs/{worker-id}.md
complete_marker: {run_dir}/outputs/{worker-id}.complete

## THE QUESTION

For EVERY function: **"How would antirez rewrite this from scratch?"**

| His answer | Verdict |
|------------|---------|
| "I wouldn't write this" | DELETE |
| "5 lines, not 50" | SIMPLIFY |
| "Inline into caller" | INLINE |
| "Like this" | KEEP |

## Instructions
1. Read file completely
2. Ask the question for EVERY function
3. Verify DELETE/INLINE with grep (callers + __all__)
4. Write findings to output_path
5. Touch complete_marker
```

## Spawn Workers

```bash
for handoff in {run_dir}/handoffs/*.md; do
    worker_id=$(basename "$handoff" .md)
    worktree_path="$HOME/.claude/worktrees/audit-${worker_id}"
    git worktree add --detach "$worktree_path" HEAD
    tmux new-session -d -s "audit-${worker_id}" -c "$worktree_path"
    tmux send-keys -t "audit-${worker_id}" \
        "HANDOFF_PATH='${handoff}' OUTPUT_PATH='${run_dir}/outputs/${worker_id}.md' claude --permission-mode dontAsk -p '/audit-worker'" Enter
done
```

## Poll Completion

```bash
while true; do
    [ "$(ls -1 {run_dir}/outputs/*.complete 2>/dev/null | wc -l)" -eq "$expected" ] && break
    sleep 30
done
```

## Cleanup

```bash
for wt in ~/.claude/worktrees/audit-*; do
    tmux kill-session -t "$(basename "$wt")" 2>/dev/null || true
    git worktree remove "$wt" 2>/dev/null || true
done
```

## Synthesis Template

```markdown
## Antirez Audit: {date}
**Files:** {n} | **LOC:** {sum} | **Deletable:** {pct}%

Every function judged by: **"How would antirez rewrite this from scratch?"**

| File | LOC | Verdict | Checkbox |
|------|-----|---------|----------|

### Verified Deletes
| File:Line | Function | LOC | Evidence |
|-----------|----------|-----|----------|

### Priority Actions
1. {highest impact first}
```
