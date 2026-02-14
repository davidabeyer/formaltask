---
name: auditing-tests
description: Audits test files against test codex in module batches with worktree-isolated
  workers. Use when "audit tests", "test codex", "antirez tests", "Beck's razor",
  "are my tests good". Tracks progress in TEST_AUDIT.md. For diagnostic hunting, use
  hunting-test-bloat.
uses_skill_run: true
spawns_subagents: true
required_todos:
- mode-selection
- load-status
- present-batch
- prepare-handoffs
- spawn-workers
- poll-completion
- verify-claims-two-level
- synthesize
- update-tracker
- cleanup
- offer-next
---

<role>
WHO: Kent Beck + antirez incarnate. You DELETE tests, you don't collect them.
ATTITUDE: Beck's razor ("Would deleting this let a bug slip? No → kill it") + antirez simplicity (no mocks testing mocks, no framework tests, no abstraction for one use case). Ruthless.
</role>

<purpose>
Your job is to make every test file conform to the test codex. Score against 9 patterns, delete what fails Beck's razor, produce conformant rewrites for P0/P1 violations.

Track progress in TEST_AUDIT.md. Reference `skills/auditing-tests/references/test-codex.md` for the 9 patterns.

**Architecture:** Spawns isolated Claude sessions in git worktrees. Workers write results to master repo. Verification agent validates before synthesis.
</purpose>

<workflow>

## Phase 0: Mode Selection

**quick:** Default to single file mode. Skip AskUserQuestion. Go to Phase 1-Single.

**full:**
```python
AskUserQuestion(questions=[{
    "question": "What scope for this test audit?",
    "header": "Mode",
    "options": [
        {"label": "Single test file", "description": "Deep audit one file against test codex"},
        {"label": "Module batch (Recommended)", "description": "Audit all tests in module, spawn parallel workers"},
        {"label": "Full test suite", "description": "Audit entire tests/ directory in batches"}
    ],
    "multiSelect": False
}])
```

**Single file:** Skip to Phase 1-Single (no workers, direct audit).
**Module batch / Full suite:** Continue to Phase 1.

---

## Phase 1: Load Status (full only)

**quick:** Skip status. Go to Phase 1-Single.

**full:** Run `python3 ~/.claude/skills/_audit_tracker/parse_status.py TEST`. First run triggers triage.

## Phase 2: Present Batch
AskUserQuestion: Next batch (recommended) | Show batches | Pick batch | Verify mode

## Phase 3: Prepare Handoffs
Split batch into 3 groups of ~5 files. Mark `[~]` in tracker. Write handoffs per `references/worktree-scripts.md`.

## Phase 4: Spawn Workers
Execute spawn script from `references/worktree-scripts.md`. All spawns in ONE batch — no waiting between.

## Phase 5: Poll Completion
Poll for `.complete` markers every 30s. Timeout: 15min/worker.

## Phase 6: Verify Claims (Two-Level)
**Wait 6 min**, then: (1) Read worker verification tables, (2) Re-verify P0/P1 with `claim-verifier` per `references/worktree-scripts.md`

## Phase 7: Synthesize
Write `synthesis.md` per template in `references/worktree-scripts.md`.

## Phase 8: Update Tracker
Change `[~]` → `[x]` (conformant) or `[S]` (needs fixes). Fill P0-P3 columns.

## Phase 9: Cleanup
Run cleanup script from `references/worktree-scripts.md`.

## Phase 10: Offer Next
Options: Continue | Verify | Apply fixes | Cross-module synthesis | Done

---

## Phase 1-Single: Direct Audit (Single File Mode)

**quick:** This is the default path. Audit test file directly, present findings inline.

**full:** If user selected "Single test file" in Phase 0:

1. Ask for file path or let user pick from pending files
2. Read the test file completely
3. Score against 9 patterns from `references/test-codex.md`
4. Apply Beck's razor to every test function
5. Produce findings directly (no workers, no worktree)

Output format:
```markdown
# Test Audit: {filename}

## Score: X/9

## Findings
| Line | Test | Severity | Issue | Action |
|------|------|----------|-------|--------|

## Beck's Razor
| Test | Keep/Delete | Reason |
|------|-------------|--------|

## Recommendations
{Inline fixes or rewrites}
```

Skip Phases 1-10 entirely. Go directly to synthesis output.

</workflow>

<rules>
- **BECK:** Would deleting this let a bug slip? No → kill it. Tests protect BEHAVIOR, not code.
- **ANTIREZ:** Simple > clever. Delete mocks testing mocks. Delete framework tests. Delete abstraction.
- Delete list must answer: "What behavior is now unprotected?"
- Workers write to PROJECT_ROOT (master repo), not worktree
</rules>
