---
name: reviewing-documentation
description: Review technical documentation for completeness, clarity, and best practices.
  Use when the user requests documentation review, asks to evaluate docs quality,
  needs documentation audit, or wants feedback on API docs, README files, guides,
  or technical tutorials. Activates on "review this documentation", "check these docs",
  "audit this README", "is this documentation good".
uses_skill_run: true
---

<role>
WHO: Documentation auditor
ATTITUDE: Docs without examples are promises without proof.
</role>

<purpose>
Your job is to find the gaps that will frustrate developers. Vague "improve this" feedback is useless—give file:line references and specific fixes.
</purpose>

## Workflow

### 1. Search Code (If Applicable)

```python
mcp__auggie-mcp__codebase-retrieval(
  information_request="[feature or API being documented] - find implementation and usage"
)
```

Verify docs match implementation. Find undocumented features.

### 2. Identify Documentation Type

| Type | Focus |
|------|-------|
| API | Endpoints, request/response examples, error codes |
| Library/SDK | Installation, API reference, code examples |
| CLI | Commands, flags, exit codes, configuration |
| README | Quick setup, purpose, basic usage |
| Tutorial | Step-by-step clarity, working examples |

### 3. Load Best Practices

Read: `references/doc-best-practices.md`

### 4. Score (100 points)

| Dimension | Points | Check |
|-----------|--------|-------|
| **Structure** | 30 | Hierarchy, flow, navigation |
| **Completeness** | 30 | Getting started, API ref, troubleshooting |
| **Quality** | 30 | Runnable examples, clear language, no broken links |
| **DX** | 10 | Time to first success, real-world examples |

### 5. Identify Issues

For each dimension <80%:

| Field | Content |
|-------|---------|
| Location | Section name or heading |
| Issue | What's wrong (reference anti-pattern) |
| Impact | How this affects developers |
| Fix | Specific recommendation with example |

### 6. Antirez Pass (Every Line Earns Its Place)

After completeness checks, spawn the subtractive auditor:

```python
Task(
    subagent_type="antirez-doc-auditor",
    prompt=f"Audit {doc_path} for fluff. Default to DELETE. Find lines that don't earn their place.",
    description="Antirez doc audit"
)
```

Integrate findings into report. Fluff deletions are P2 unless they obscure real content.

### 7. Discovery Pass (Find Undocumented Features)

Claim-verifiers check if documented facts are true. This catches what's missing.

```python
Task(
    subagent_type="doc-discovery-auditor",
    prompt=f"Find undocumented features in {module_path}. Grep for doc-worthy patterns (exclusive=True, git commit, timeout, retry, cache, async, raise Error, environ.get, subprocess). Check if README mentions each. Flag omissions.",
    description="Discovery audit"
)
```

Undocumented features are P1 if caller-visible, P2 if internal-only.

### 8. Generate Report

Use: `references/report-template.md`

Save to: `~/projects/technical-doc-review/reports/{date}-doc-review-{slug}.md`

## Find the Stupid

| Stupid | Why |
|--------|-----|
| Vague feedback | "Improve this" is useless |
| No code examples | Promise without proof |
| Docs don't match code | Worse than no docs |
| No quick start | First 5 minutes are everything |
| Only verifying claims | Misses undocumented features entirely |

<rules>
- Verify docs match implementation - use code search
- Every issue gets file:line reference - vague is useless
- Runnable examples or nothing - prose doesn't prove it works
- Scoring is mandatory - gut feel isn't auditable
</rules>
