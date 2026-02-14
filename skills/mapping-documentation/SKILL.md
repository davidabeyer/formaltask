---
name: mapping-documentation
description: Two-wave documentation mapping from code. Wave 1 (3 agents) maps topology, API,
  complexity. Wave 2 (N worktree workers) deep-dives modules. Ignores stale docs. Use when
  "document codebase", "what needs docs", "doc mapping".
uses_skill_run: true
spawns_subagents: true
required_todos:
- spawn-wave1
- merge-wave1
- spawn-wave2
- synthesize
---

<role>
WHO: Documentation archaeologist
ATTITUDE: Existing docs are lies. Code is truth.
</role>

<purpose>
Your job is to produce a prioritized documentation roadmap from code alone.

Two waves → `synthesis.md` with P0/P1/P2/P3 gaps and recommended order.
</purpose>

<workflow>

## Phase 0: Size Check

```bash
module_count=$(find . -name "*.py" -path "*/[a-z]*/" | cut -d/ -f2 | sort -u | wc -l)
```

If <= 2: Skip waves. Do direct analysis → Phase 5.

## Phase 1: Wave 1 (Discovery)

Spawn 3 agents. **ALL in ONE message:**

```python
Task(subagent_type="general-purpose", description="Map topology", run_in_background=True,
    prompt=f"""Map module structure. Count files, LOC, imports.
MODULE NAMING: path format (formaltask/cli NOT formaltask.cli)
OUTPUT: {run_dir}/wave1/topology.md
Format: | Module | Files | LOC | Imports From | Imported By |""")

Task(subagent_type="general-purpose", description="Scan API", run_in_background=True,
    prompt=f"""Find public symbols. Count callers. Flag undocumented.
MODULE NAMING: path format
OUTPUT: {run_dir}/wave1/api-surface.md
Format: | Module | Symbol | Type | Callers | Has Docstring |""")

Task(subagent_type="general-purpose", description="Profile complexity", run_in_background=True,
    prompt=f"""Score modules by complexity. Identify hotspots.
MODULE NAMING: path format
OUTPUT: {run_dir}/wave1/complexity.md
Format: | Module | Score | Max Nesting | Avg Func LOC | Hotspots |""")
```

**EXIT:** All 3 outputs exist.

## Phase 2: Merge + Assign

Read wave1 outputs. Calculate priority:
```
score = (public_symbols * 2) + (callers * 1.5) + (complexity * 2)
```

Worker count:
| Modules | Workers |
|---------|---------|
| <= 3 | 2 |
| 4-6 | 4 |
| 7+ | 6 |

Round-robin assign sorted modules to workers.

## Phase 3: Prepare Handoffs

Write to `{run_dir}/handoffs/{worker_id}.md`. Use **ABSOLUTE paths**.

```markdown
## Assignment
output_path: {ABSOLUTE}/outputs/{id}.md
complete_marker: {ABSOLUTE}/outputs/{id}.complete

## Modules
- {module1}
- {module2}

## Priority Targets
| Symbol | Callers | Why |

## Done When
1. All modules analyzed
2. Output written
3. touch complete_marker
```

## Phase 4: Wave 2 (Workers)

```bash
for handoff in {run_dir}/handoffs/*.md; do
    id=$(basename "$handoff" .md)
    wt="$HOME/.claude/worktrees/docmap-${id}"
    git worktree add --detach "$wt" HEAD
    tmux new-session -d -s "docmap-${id}" -c "$wt" \
        -e "HANDOFF_PATH=${handoff}" \
        -e "OUTPUT_PATH={run_dir}/outputs/${id}.md" \
        bash --norc --noprofile
    tmux send-keys -t "docmap-${id}" \
        "claude --permission-mode dontAsk -p '/doc-mapping-worker'" Enter
done
```

Poll:
```bash
while [ $(ls {run_dir}/outputs/*.complete 2>/dev/null | wc -l) -lt $expected ]; do sleep 30; done
```

## Phase 5: Synthesize

Merge into `{run_dir}/synthesis.md`:

```markdown
# Documentation Map
**Generated:** {date} | **Modules:** {n} | **Workers:** {n}

## P0: Critical (Public + Many Callers + No Docs)
| Module | Symbol | Callers | Fix |

## P1: Important (Complex + No Explanation)
| Module | Symbol | Complexity | Fix |

## P2/P3: Valuable / Nice-to-Have
[Grouped]

## Recommended Order
1. **{module}** — {why first}
2. **{module}** — {why second}

## Quick Wins
- {N} need docstrings
- {N} need README

## Skip These
[Self-documenting, internal-only]
```

## Phase 6: Cleanup

```bash
for wt in ~/.claude/worktrees/docmap-*; do
    tmux kill-session -t "$(basename "$wt")" 2>/dev/null || true
    git worktree remove --force "$wt" 2>/dev/null || true
done
```

</workflow>

<rules>
- Code is truth. Ignore existing docs.
- ALL spawns in ONE message. Sequential defeats parallel.
- Handoffs use ABSOLUTE paths. Workers don't know {run_dir}.
- Adaptive sizing. 2-6 workers based on module count.
- Tiny codebase (<=2 modules) → direct analysis, skip waves.
- synthesis.md is REQUIRED. No output = failed.
</rules>
