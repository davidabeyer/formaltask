---
consumes: [batch-assignments]
produces: [batch-outputs]
optional: true
---

**quick:** Skip subagents. Audit tests yourself in synthesize step.

**full:** **ALL Task calls in ONE message for parallel execution.**

```python
Task(
    subagent_type="test-quality-auditor",
    description=f"Test audit batch 1/{n}",
    prompt=f"""[BATCH 1/{n}] RUTHLESS TEST AUDIT

FILES:
{batch_1_files}

HUNT FOR:
1. FAKE TESTS (P0): No assertions, mock everything, pass regardless
2. WEAK ASSERTIONS (P1): Truthy checks, type-only, missing edge cases
3. ANTIREZ VIOLATIONS (P1): Over-abstracted helpers, test > code length
4. SIZE/FOCUS (P2): >300 lines, tests multiple behaviors
5. ISOLATION (P2): Shared state, order dependencies
6. ANTI-PATTERNS (P3): Magic numbers, copy-paste, hardcoded paths

OUTPUT JSON to: {output_path}/batch-1.json
{{
  "batch": 1,
  "files_audited": N,
  "score": 0-100,
  "findings": [
    {{"severity": "P0", "file": "path", "line": N, "issue": "...", "fix": "..."}}
  ]
}}""",
    run_in_background=True
)
# Repeat for all batches in SAME message
```

**EXIT CRITERIA:** All batches launched
