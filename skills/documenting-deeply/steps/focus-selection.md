---
consumes: [code-understanding]
produces: [focus-area]
---
# Phase 2: Focus Area Selection

Based on discovery, select area for deep documentation.

## Selection Priority

1. User-specified area (if any)
2. Gaps: No documentation exists
3. Staleness: Code changed recently, docs didn't (`git log --since='3 months ago'`)
4. Incorrectness: Docs don't match behavior

## Output

Write selection to `{run.run_dir}/02-focus-selection.md` with path, reason, and target doc file.
