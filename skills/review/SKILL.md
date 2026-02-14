---
name: review
description: Unified code review router. Detects patterns, proposes reviewers, spawns
  in parallel. Use "review", "review my changes", "review PR
argument-hint: <target> [--quick|--thorough|--security]
inherit:
- review
tools:
- auggie
- warpgrep
spawns_subagents: true
required_todos:
- detect-target
- analyze-patterns
- propose-reviewers
- spawn-reviewers
- synthesize
---

<role>
WHO: Review orchestrator
ATTITUDE: Right reviewers catch right bugs. Wrong reviewers waste tokens.
</role>

<purpose>
Detect target, analyze patterns, propose reviewers via checkboxes, spawn parallel, synthesize.
</purpose>

<workflow>

## Phase 0: Detect Target

**quick:** Auto-detect target. Skip to Phase 3 with code-quality-auditor only.

**full:**
| Input | Action |
|-------|--------|
| `123` or `PR #123` | `gh pr diff 123` |
| `file.py` | `git diff HEAD -- file.py` |
| (none) | `git diff HEAD` |

Extract: files changed, file types, line counts.

---

## Phase 1: Analyze Patterns

**quick:** Skip pattern analysis. Use code-quality-auditor only.

**full:** Scan diff for signals → map to reviewers:

| Signal | Reviewer |
|--------|----------|
| `sqlite3`, `cursor.execute` | sqlite-reviewer |
| `subprocess`, `Popen`, `os.system` | subprocess-reviewer |
| `Path(`, `os.path`, `open(` | path-security-reviewer |
| `os.environ`, `getenv`, API keys | configuration-auditor |
| `try:`, `except`, `raise` | error-handling-reviewer |
| `BaseModel`, `Field(`, validator | schema-reviewer |
| `hooks/`, `PreToolUse` | hook-reviewer |
| `test_`, `pytest`, `assert` | test-quality-auditor |
| `Enum`, status transitions | state-machine-reviewer |
| `tmux`, TUI widgets | tui-reviewer |
| `requests`, `httpx`, API calls | api-client-reviewer |
| Large loops, recursion | performance-auditor |
| `input(`, `args.`, CLI args | input-validation-reviewer |

**Always:** `code-quality-auditor`

Build: detected (pre-checked) + available (unchecked).

---

## Phase 2: Propose Reviewers (full only)

**quick:** Skip AskUserQuestion. Use detected reviewers automatically.

**full:**
```python
AskUserQuestion(questions=[{
    "question": "Which reviewers?",
    "header": "Review",
    "options": [
        {"label": "code-quality (Recommended)", "description": "Quality, antirez style"},
        {"label": "sqlite-reviewer", "description": "Detected: SQL in diff"},
        # ... detected first, then available
    ],
    "multiSelect": True
}])
```

**Profiles:** `--quick` (quality only), `--thorough` (all detected + test), `--security` (security + path + input + config)

---

## Phase 3: Spawn Reviewers

**quick:** Review diff yourself applying code-quality checks. Report findings inline.

**full:** ALL in SINGLE message (parallel):

```python
Task(subagent_type="code-quality-auditor", model="sonnet", run_in_background=True,
     prompt=f"Review diff:\n{diff}")
Task(subagent_type="sqlite-reviewer", model="sonnet", run_in_background=True,
     prompt=f"Review diff:\n{diff}")
```

Wait for all. Collect outputs.

---

## Phase 4: Synthesize

**quick:** Present findings inline with verdict. Skip formal synthesis.

**full:**
1. **De-dupe:** Same file:line → merge, keep best fix
2. **Prioritize:** P0 (blocking) → P1 (fix) → P2 (consider)
3. **Group by file**

```
REVIEW: {target} | {N} findings | {reviewers}
─────────────────────────────────────────────
P0 - Blocking
  file.py:42 [sqlite] SQL injection risk

P1 - Should Fix
  file.py:15 [quality] Function >50 lines
─────────────────────────────────────────────
Verdict: PASS | FIX_REQUIRED | BLOCKED
```

**Verdict:** P0>0 → BLOCKED, P1>2 → FIX_REQUIRED, else PASS

</workflow>

<rules>
- Always include code-quality-auditor
- Detected = pre-checked, available = unchecked
- Spawn ALL in single message
- P0 blocks, no exceptions
</rules>
