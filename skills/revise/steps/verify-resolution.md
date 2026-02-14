---
consumes: [verified-findings]
produces: [revision-report]
---
# Phase 4 + 5: Verify Fixes + Output

## Phase 4: Verify Fixes

Re-run lightweight checks (no auditor spawn):
- File paths still valid?
- Dependencies still consistent? No circular deps?
- Interfaces match across specs?

**EXIT CRITERIA:** Self-verification passed.

---

## Phase 5: Output

Publish report via `run.publish_report(f"{project}-{target_type.lower()}-revision-round{current_round}.md")`.

**MANDATORY output format:**

```markdown
# Revision Round {N}

## Findings Table

| ID | Priority | Finding | Resolution | Evidence |
|----|----------|---------|------------|----------|
| P0-1 | P0 | [finding] | fixed | Lines X-Y in plan.yaml |
| P1-1 | P1 | [finding] | rejected | [grep evidence: critique was wrong] |
| P1-2 | P1 | [finding] | deferred | Already addressed in prior round |
```

**Resolution values match history entries:** fixed, rejected, deferred.

**If ANY cell is empty -> ABORT and re-run Phase 4 verification.**

Report also contains: changes by file, summary (fixed/skipped counts).

Display: `REVISED: {project} ({target_type})` with fixed/skipped counts. Next step: `/critique {project}`.

After publishing report:
```python
Bash(command=f"cd {plans_dir} && git add -A && git commit -m 'revise: {project} round {current_round}'")
```

**EXIT CRITERIA:** Report written with complete findings table, committed to git, next step displayed.
