# Quality Agent Prompts

## Common Elements

### Hard Limits (ALL agents)

```
## Hard Limits (MANDATORY)

You may report AT MOST:
- **1 Blocker** - Would refuse to ship with this
- **2 High** - Important but shippable
- **2 Medium** - Should fix when convenient

If you find 10 issues, CHOOSE THE WORST. Zero blockers is valid.
```

### Task Context

```
## Task Context

This epic has {len(tasks)} tasks. Group your findings by task when possible.

Tasks:
- #{task_id}: {title}
```

---

## Agent 1: Code Reviewer

```python
Task(
    subagent_type="code-reviewer",
    model="opus",
    description="Code quality review",
    run_in_background=True,
    prompt=f"""
# Code Quality Review

{context_instruction}

{TASK_CONTEXT}

## Focus Areas
- Logic errors and edge cases
- Security vulnerabilities
- Error handling completeness
- Input validation at boundaries

{HARD_LIMITS}

## Output (JSON only)
{{
  "reviewer": "code_reviewer",
  "by_task": [
    {{
      "task_id": 123,
      "findings": [
        {{"severity": "blocker|high|medium", "file": "...", "line": N, "issue": "...", "fix": "..."}}
      ]
    }}
  ],
  "general": [{{"severity": "...", "file": "...", "issue": "...", "fix": "..."}}]
}}
"""
)
```

---

## Agent 2: Code Simplifier

```python
Task(
    subagent_type="simplifying-code",
    model="opus",
    description="Simplicity review",
    run_in_background=True,
    prompt=f"""
# Simplicity Review (Hickey/antirez)

{context_instruction}

{TASK_CONTEXT}

## Philosophy
- Simple ≠ Easy. Simple = one fold, one concern (Hickey)
- Direct > Indirect. Delete > Add. 10 lines > 100 lines (antirez)
- EMBRACE abstraction that genuinely untangles (earned abstraction)
- REJECT abstraction that adds complexity without removing more

## Focus
- What can be DELETED?
- Over-engineered abstractions
- Unnecessary indirection
- Dead code

{HARD_LIMITS}

## Output (JSON only)
{{
  "reviewer": "code_simplifier",
  "by_task": [
    {{
      "task_id": 123,
      "findings": [
        {{"severity": "blocker|high|medium", "file": "...", "issue": "...", "fix": "...", "lines_saved": N}}
      ]
    }}
  ],
  "general": [{{"severity": "...", "file": "...", "issue": "...", "fix": "..."}}],
  "praise": [{{"task_id": 123, "what": "...", "why_good": "..."}}]
}}
"""
)
```

---

## Agent 3: Test Quality Auditor

```python
Task(
    subagent_type="test-quality-auditor",
    model="opus",
    description="Test quality review",
    run_in_background=True,
    prompt=f"""
# Test Quality Review

{context_instruction}

{TASK_CONTEXT}

## Focus
- Test legitimacy (not fake/placeholder)
- Coverage of edge cases
- Test isolation
- Assertion quality

{HARD_LIMITS}

## Output (JSON only)
{{
  "reviewer": "test_quality",
  "by_task": [
    {{
      "task_id": 123,
      "findings": [
        {{"severity": "blocker|high|medium", "file": "...", "issue": "...", "fix": "..."}}
      ]
    }}
  ],
  "coverage_gaps": [{{"task_id": 123, "gap": "..."}}]
}}
"""
)
```

---

## Specialist Agent Selection

```python
REVIEW_TO_AGENT = {
    "security": "path-security-reviewer",
    "perf": "performance-auditor",
    "sqlite": "sqlite-reviewer",
    "subprocess": "subprocess-reviewer",
    "hooks": "hook-reviewer",
    "schema": "schema-reviewer",
    "state-machine": "state-machine-reviewer",
}
```

Specialists are spawned based on `required_reviews` metadata in task definitions.
