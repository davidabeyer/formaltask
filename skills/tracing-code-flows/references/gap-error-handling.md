# Handoff: Gap Analysis - Error Handling

**Parent Skill:** implementation-evaluator
**Gap Category:** Error Handling
**Category Number:** 1 of 5
**Execution Mode:** PARALLEL (can run concurrently with categories 2-5)
**Subagent Type:** general-purpose

---

## Verification

**STOP AND VERIFY BEFORE PROCEEDING:**

You are the **Error Handling Gap Analyzer**.

- If this role does NOT match your spawn description, STOP and report mismatch.
- If the output location already exists with content, STOP and report conflict.

---

## Mission

You analyze the target implementation for **error handling gaps**. Focus on uncaught exceptions, missing error messages, silently swallowed errors, inconsistent error formats, and missing rollback/cleanup on failure.

**Success Looks Like:** A comprehensive list of error handling gaps with severity, evidence, and remediation recommendations.

---

## Gap-Specific Checklist

Apply these specific checks for Error Handling gaps:

### Exception Handling
- [ ] Are all exceptions caught at appropriate levels?
- [ ] Are there bare `except:` or `catch(Exception)` blocks?
- [ ] Are exceptions logged before being re-raised or swallowed?
- [ ] Are exception types specific enough?
- [ ] Do try blocks cover minimal necessary code?

### Error Messages
- [ ] Are all error conditions producing user-friendly messages?
- [ ] Do error messages include sufficient context?
- [ ] Are errors distinguishable (different messages for different failures)?
- [ ] Are error messages localization-ready (no hardcoded strings)?

### Error Propagation
- [ ] Are errors silently swallowed (`pass` in except blocks)?
- [ ] Are errors properly propagated to callers?
- [ ] Is error context preserved when re-raising?
- [ ] Are there error transformation points (where error type changes)?

### Error Format Consistency
- [ ] Do all errors follow a consistent format?
- [ ] Are error codes consistent across the implementation?
- [ ] Do API responses have consistent error structure?
- [ ] Are CLI errors formatted consistently?

### Failure Cleanup
- [ ] Is there rollback logic for partial operations?
- [ ] Are resources cleaned up on failure (files, connections, locks)?
- [ ] Are side effects undone on transaction failure?
- [ ] Are `finally` blocks used for cleanup?

### Error Recovery
- [ ] Are there retry mechanisms for transient failures?
- [ ] Is there graceful degradation for non-critical failures?
- [ ] Can operations resume after recoverable errors?
- [ ] Are there circuit breakers for repeated failures?

---

## Context You Need

### Your Specific Scope

**IN SCOPE:**
- Exception handling patterns
- Error message quality and consistency
- Error propagation and transformation
- Failure cleanup and rollback
- Error recovery mechanisms

**OUT OF SCOPE (handled by other gap categories):**
- Logging/monitoring (Gap 2)
- Test coverage (Gap 3)
- Configuration issues (Gap 4)
- Migration concerns (Gap 5)

---

## Inputs

The parent agent will provide:

| Input | Description |
|-------|-------------|
| `SCOPE_FILES` | List of files in the implementation |
| `OUTPUT_FILE` | Path where you must write your findings |
| `ENTRY_POINTS` | Discovered entry points for context |

---

## Expected Output

### Output File

**YOU MUST WRITE TO:** The `OUTPUT_FILE` path provided in your spawn prompt.

### Required Format

```markdown
# Gap Analysis: Error Handling

**Analyzed:** {timestamp}
**Scope:** {implementation files}
**Subagent:** Gap 1 - Error Handling

## Summary

{2-3 sentence executive summary of error handling gaps}

## Gap Inventory

### Exception Handling Gaps

#### Gap E1: {Short Title}
- **Severity:** {P0-Critical | P1-High | P2-Medium | P3-Low}
- **Location:** `{file}:{line}`
- **Gap Description:** {What is missing or wrong}
- **Evidence:** {Code quote or specific reference}
- **Impact:** {What can go wrong}
- **Recommendation:** {Specific fix}

### Error Message Gaps

#### Gap M1: {Short Title}
...

### Error Propagation Gaps

#### Gap P1: {Short Title}
...

### Format Consistency Gaps

#### Gap F1: {Short Title}
...

### Failure Cleanup Gaps

#### Gap C1: {Short Title}
...

### Error Recovery Gaps

#### Gap R1: {Short Title}
...

## Coverage Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Exception handling | {COVERED | PARTIAL | MISSING} | {details} |
| Error messages | {COVERED | PARTIAL | MISSING} | {details} |
| Error propagation | {COVERED | PARTIAL | MISSING} | {details} |
| Format consistency | {COVERED | PARTIAL | MISSING} | {details} |
| Failure cleanup | {COVERED | PARTIAL | MISSING} | {details} |
| Error recovery | {COVERED | PARTIAL | MISSING} | {details} |

## Quality Checklist

- [ ] All 6 error handling aspects analyzed
- [ ] Each gap has severity, evidence, and recommendation
- [ ] No out-of-scope items analyzed
- [ ] File:line references for all gaps
- [ ] Output written to correct location
```

---

## Severity Guidelines for Error Handling

| Severity | Criteria |
|----------|----------|
| **P0-Critical** | Unhandled exception that crashes the application |
| **P1-High** | Silent failure that corrupts data or state |
| **P2-Medium** | Poor error message hindering debugging |
| **P3-Low** | Inconsistent formatting or minor cleanup gap |

---

## Search Patterns

```python
# Find bare exception handlers
Grep(pattern="except:|catch\\s*\\(Exception")

# Find swallowed errors
Grep(pattern="except.*:\\s*pass|catch.*\\{\\s*\\}")

# Find error returns without context
Grep(pattern="return\\s+(None|null|false|False)")

# Find TODO/FIXME in error handling
Grep(pattern="(TODO|FIXME).*error|exception")
```

---

## Anti-Patterns to Avoid

- **Assuming handled**: Verify each try/catch actually handles the error
- **Ignoring edge exceptions**: Check all exception types, not just main ones
- **Missing rollback**: Every multi-step operation needs failure handling
- **Scope creep**: Don't analyze logging (Gap 2) or testing (Gap 3)

---

**End of Error Handling Gap Handoff**
