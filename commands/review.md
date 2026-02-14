---
name: review
description: "Fast ad-hoc code review for uncommitted work with 3 focused reviewers"
argument-hint: "[security|perf] or blank for general review"
allowed-tools: Bash, Read, Glob, Grep, Task, mcp__auggie-mcp__codebase-retrieval, mcp__morph-mcp__warpgrep_codebase_search
---

# /review [mode]

Fast code review for ad-hoc work. Spawns 3 blocking opus agents.

## Modes

| Mode | Focus |
|------|-------|
| `default` | General code quality, logic, tests |
| `security` | Auth, input handling, injection, secrets |
| `perf` | N+1 queries, loops, caching, memory |

---

## Part 1: Determine Context

Review session work if available, otherwise uncommitted changes:

```bash
git diff --name-status HEAD
git diff --cached --name-status
```

If no changes: "No uncommitted changes to review."

---

## Part 2: Parse Mode

```python
mode = "$ARGUMENTS".strip().lower() or "default"

FOCUS_PROMPTS = {
    "default": "Focus on correctness, edge cases, error handling, test coverage, and code clarity.",
    "security": "Focus on authentication, authorization, input validation, injection attacks, secrets exposure, and OWASP Top 10.",
    "perf": "Focus on N+1 queries, unnecessary loops, missing caching, memory leaks, and algorithmic complexity."
}
```

---

## Part 3: Spawn 3 Reviewers (BLOCKING)

Spawn all 3 in a **SINGLE message** (no `run_in_background`):

```python
HARD_LIMITS = """
## Hard Limits (MANDATORY)

You may report AT MOST:
- **1 Blocker** - Would refuse to ship with this
- **2 High** - Important but shippable
- **2 Medium** - Should fix when convenient

If you find 10 issues, CHOOSE THE WORST. Zero blockers is valid.
"""

CONTEXT_INSTRUCTION = """
## Context Source

{context_description}

{If session work: "Review the changes made in this conversation."}
{If git diff: "Run `git diff HEAD` to see uncommitted changes."}
"""
```

### Reviewer 1: Code Reviewer

```python
Task(
    subagent_type="code-reviewer",
    model="opus",
    description="Code quality review",
    prompt=f"""
# Code Quality Review

{CONTEXT_INSTRUCTION}

## Codebase Understanding

**Use MCP tools to understand context before reviewing:**

```python
mcp__auggie-mcp__codebase-retrieval(
    information_request="Related implementations and patterns for the code being reviewed"
)

mcp__morph-mcp__warpgrep_codebase_search(
    search_string="How does this code integrate with the rest of the codebase?",
    repo_path=project_root
)
```

## Your Focus
{FOCUS_PROMPTS[mode]}

{HARD_LIMITS}

## Output (JSON only)
```json
{{
  "reviewer": "code_reviewer",
  "blocker": null or {{"file": "...", "line": N, "issue": "...", "fix": "..."}},
  "high": [{{"file": "...", "line": N, "issue": "...", "fix": "..."}}],
  "medium": [{{"file": "...", "line": N, "issue": "...", "fix": "..."}}]
}}
```

Return ONLY the JSON, no other text.
"""
)
```

### Reviewer 2: Code Simplifier

```python
Task(
    subagent_type="code-simplifier",
    model="opus",
    description="Simplicity review",
    prompt=f"""
# Simplicity Review (Hickey/antirez)

{CONTEXT_INSTRUCTION}

## Your Philosophy
- Simple ≠ Easy. Simple = one fold, one concern (Hickey)
- Direct > Indirect. Delete > Add. 10 lines > 100 lines (antirez)
- EMBRACE abstraction that genuinely untangles (earned abstraction)
- REJECT abstraction that adds complexity without removing more

## Your Territory
- Over-engineering, unnecessary indirection
- Complected concepts that should be separated
- Code that should be DELETED
- BUT ALSO: missed opportunities for simplifying abstractions

{HARD_LIMITS}

## Output (JSON only)
```json
{{
  "reviewer": "code_simplifier",
  "blocker": null or {{"file": "...", "issue": "...", "fix": "...", "lines_saved": N}},
  "high": [{{"file": "...", "issue": "...", "recommendation": "..."}}],
  "medium": [{{"file": "...", "issue": "...", "recommendation": "..."}}],
  "praise": [{{"file": "...", "what": "...", "why_good": "..."}}]
}}
```

Return ONLY the JSON, no other text.
"""
)
```

### Reviewer 3: Test Quality Auditor

```python
Task(
    subagent_type="test-quality-auditor",
    model="opus",
    description="Test quality review",
    prompt=f"""
# Test Quality Review

{CONTEXT_INSTRUCTION}

## Your Focus
- Test legitimacy (not fake/placeholder tests)
- Coverage of edge cases and error paths
- Test isolation (no hidden dependencies)
- Assertion quality (meaningful, not trivial)

{HARD_LIMITS}

## Output (JSON only)
```json
{{
  "reviewer": "test_quality",
  "blocker": null or {{"file": "...", "issue": "...", "evidence": "..."}},
  "high": [{{"file": "...", "issue": "...", "recommendation": "..."}}],
  "medium": [{{"file": "...", "issue": "...", "recommendation": "..."}}],
  "coverage_gaps": ["Untested scenario 1", "Untested scenario 2"]
}}
```

Return ONLY the JSON, no other text.
"""
)
```

---

## Part 4: Synthesize

```python
# Count issues from all reviewers
blockers = [f["blocker"] for f in findings.values() if f.get("blocker")]
high = [item for f in findings.values() for item in f.get("high", [])]
medium = [item for f in findings.values() for item in f.get("medium", [])]
praise = findings.get("code_simplifier", {}).get("praise", [])
coverage_gaps = findings.get("test_quality", {}).get("coverage_gaps", [])

# Determine verdict
if len(blockers) >= 2:
    verdict = "RETHINK"
elif len(blockers) == 1:
    verdict = "FIX_BLOCKER"
elif len(high) > 2:
    verdict = "NEEDS_FIXES"
else:
    verdict = "APPROVED"
```

---

## Part 5: Output Report

```markdown
# Code Review: {mode} mode

## Verdict: {verdict}

---

## Blockers ({len(blockers)})

{For each blocker:}
### [{reviewer}] {file}:{line}
{issue}
**Fix**: {fix}

---

## High Priority ({len(high)})

{For each:}
- **[{reviewer}]** {file}:{line} - {issue}
  Fix: {fix or recommendation}

---

## Medium Priority ({len(medium)})

{For each:}
- [{reviewer}] {file} - {issue}

---

## What's Good

{For each praise:}
- {file}: {what} - {why_good}

---

## Test Coverage Gaps

{For each gap:}
- {gap}

---

## Summary

| Reviewer | Blocker | High | Medium |
|----------|---------|------|--------|
| Code Reviewer | {0 or 1} | {n} | {n} |
| Code Simplifier | {0 or 1} | {n} | {n} |
| Test Quality | {0 or 1} | {n} | {n} |
```

---

## Next Step

If verdict is not APPROVED, run `/review-fix-planning` to convert findings into an actionable fix plan with file:line targets.
