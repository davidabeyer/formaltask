# Orchestration Patterns

Shared patterns for skills that spawn parallel workers in worktrees or as Task() subagents.

## Spawn Pattern (Worktree + tmux)

Use when workers need filesystem isolation.

```bash
for handoff in {run_dir}/handoffs/*.md; do
    worker_id=$(basename "$handoff" .md)
    worktree_path="$HOME/.claude/worktrees/{skill}-${worker_id}"

    git worktree add --detach "$worktree_path" HEAD

    tmux new-session -d \
        -s "{skill}-${worker_id}" \
        -c "$worktree_path" \
        -e "PROJECT_ROOT=$(git rev-parse --show-toplevel)" \
        -e "HANDOFF_PATH=${handoff}" \
        -e "OUTPUT_PATH={run_dir}/outputs/${worker_id}.md" \
        bash --norc --noprofile

    tmux send-keys -t "{skill}-${worker_id}" \
        "export HANDOFF_PATH='${handoff}' && export OUTPUT_PATH='{run_dir}/outputs/${worker_id}.md' && claude --permission-mode dontAsk -p '/{worker-skill}'" \
        Enter
done
```

**Template variables:**
- `{skill}` - parent skill name (e.g., `audit-tests`)
- `{run_dir}` - skill run directory with handoffs/outputs
- `{worker_id}` - unique worker identifier (uuid[:8])
- `{worker-skill}` - skill the worker runs (e.g., `test-audit-worker`)

## Spawn Pattern (Task subagents)

Use when workers don't need filesystem isolation.

```python
for i, target in enumerate(targets):
    Task(
        subagent_type="{worker-agent}",
        description=f"{skill}: {target}",
        run_in_background=True,
        prompt=f"""## TARGET
{target}

## OUTPUT PATH
Write findings to: {outputs}/{worker_id}.md

## DONE WHEN
- Target fully analyzed
- Output written to assigned path
- Do NOT write to synthesis.md
"""
    )
```

All spawns in ONE message for true parallel execution.

## Poll Completion

### For worktree workers (file markers)

```bash
while true; do
    complete_count=$(ls -1 {run_dir}/outputs/*.complete 2>/dev/null | wc -l)
    [ "$complete_count" -eq "$expected_count" ] && break
    sleep 30
done
```

### For Task subagents

Use `run_in_background=True` and wait for all Task results in single message.

## Cleanup (Worktree)

```bash
for worktree in ~/.claude/worktrees/{skill}-*; do
    tmux kill-session -t "$(basename "$worktree")" 2>/dev/null || true
    git worktree remove --force "$worktree" 2>/dev/null || true
done
```

## Handoff Template

Workers are context-blind. Include everything they need.

```markdown
## Worker Assignment
worker_id: {uuid[:8]}
output_path: {run_dir}/outputs/{worker_id}.md
complete_marker: {run_dir}/outputs/{worker_id}.complete

## Files
- {file1}
- {file2}

## Instructions
{FULL instructions - workers have zero parent context}

## Output Format
{EXACT format expected - workers don't know synthesis needs}

## Done When
1. All files processed
2. Output written to output_path
3. Touch complete_marker
```

## Synthesis Template

Orchestrator reads all worker outputs and synthesizes.

```markdown
# {Skill} Synthesis

**Date:** {date}
**Workers:** {count}
**Targets:** {total}

## Summary by Severity
| Severity | Count | Top Categories |
|----------|-------|----------------|
| P0 | N | {categories} |
| P1 | N | {categories} |

## Cross-Target Patterns
{Issues appearing in 3+ targets - codebase-wide}

## Hotspots
| Target | P0 | P1 | P2 | Total |
|--------|----|----|----|----|

## Quick Wins
1. {batch fix with count}
```

## Re-Verification Pattern

Workers may miss cross-file issues. Re-verify P0/P1 claims before synthesis.

```python
Task(
    subagent_type="claim-verifier",
    description="Re-verify aggregated P0/P1 claims",
    prompt=f"""Verify these claims from workers.

For each claim, check:
1. Is this actually true?
2. Would this fix break something else?

Claims:
{claims}
"""
)
```

## Rules

- **ALL spawns in ONE message** - sequential defeats parallel
- **Workers write to PROJECT_ROOT** (not worktree) for results
- **Handoffs are COMPLETE** - workers have zero parent context
- **Synthesis is MANDATORY** - parallel without synthesis wastes the pattern
- **Re-verify P0/P1** before synthesis - workers miss cross-file issues
