# Task Specification Format

## Mandatory Task Format

```markdown
#### Task: [Verb] [Object] [Context]

**Epic:** {epic_name}
**Priority:** P{N} - {Critical/High/Medium/Low}
**Estimated Effort:** {30min/1hr/2hr}

**File(s):**
- `path/to/file.py:line-range` (modify)

**Description:**
[2-3 sentences describing the specific change, why it matters, and expected outcome]

**Details:**
- [Specific implementation detail with code reference]
- [Another detail with pattern reference]
- [Related change if applicable]

**Acceptance Criteria:**
- [ ] [Binary testable criterion 1]
- [ ] [Binary testable criterion 2]
- [ ] [Test exists and passes]

**Findings Addressed:**
- {file:line} - {finding description} (P{N})
- {file:line} - {finding description} (P{N})

**Reference:** Pattern in `path/to/example.py:45-67`
```

---

## Quality Standards

### Title Must Be:
- Verb-first (Fix, Add, Refactor, Implement, Update)
- Specific (not "Fix security issues" but "Add path validation to file operations")
- Scoped (references specific component/file)

### Acceptance Criteria Must Be:
- Binary (pass/fail, yes/no)
- Independently verifiable
- Include test verification

### Details Must Include:
- Specific file:line references
- Pattern to follow (existing code)
- Edge cases to handle

---

## Anti-Patterns to Avoid

```markdown
BAD TASK TITLES:
- "Fix P0 issues" - Too vague
- "Security improvements" - No specificity
- "Update tests" - Which tests? How?

BAD ACCEPTANCE CRITERIA:
- "Code is secure" - Not testable
- "Tests pass" - Too generic
- "Performance improved" - No metric

BAD DETAILS:
- No file references
- No pattern references
- "See review report" - Must be self-contained
```

---

## Verification Before Completion

Before marking task plan complete, verify:

- [ ] All findings from review are addressed (no orphans)
- [ ] P0 findings have P0 tasks (priority preserved)
- [ ] Each task has specific file:line references
- [ ] Each task has binary testable acceptance criteria
- [ ] Each task is right-sized (30 min - 2 hr)
- [ ] Dependencies are explicitly mapped
- [ ] Execution order respects priority and dependencies
- [ ] No vague task titles ("Fix issues", "Update code")
- [ ] No placeholder descriptions ("See review for details")
