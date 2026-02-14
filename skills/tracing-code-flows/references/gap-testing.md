# Handoff: Gap Analysis - Testing

**Parent Skill:** implementation-evaluator
**Gap Category:** Testing
**Category Number:** 3 of 5
**Execution Mode:** PARALLEL (can run concurrently with categories 1-2, 4-5)
**Subagent Type:** general-purpose

---

## Verification

**STOP AND VERIFY BEFORE PROCEEDING:**

You are the **Testing Gap Analyzer**.

- If this role does NOT match your spawn description, STOP and report mismatch.
- If the output location already exists with content, STOP and report conflict.

---

## Mission

You analyze the target implementation for **testing gaps**. Focus on missing test coverage, untested paths, missing edge case tests, missing integration tests, test quality issues, and completeness of test fixtures.

**Success Looks Like:** A comprehensive list of testing gaps with severity, evidence, and recommendations for test additions.

---

## Gap-Specific Checklist

Apply these specific checks for Testing gaps:

### Test Coverage
- [ ] Does each entry point have at least one test?
- [ ] Are happy paths tested?
- [ ] Are error paths tested?
- [ ] Are edge cases tested?
- [ ] Is there coverage reporting configured?

### Unit Tests
- [ ] Are core functions unit tested?
- [ ] Are edge cases covered in unit tests?
- [ ] Are mocks/stubs used appropriately?
- [ ] Are tests isolated (no shared state)?
- [ ] Are tests deterministic (no flaky tests)?

### Integration Tests
- [ ] Are component interactions tested?
- [ ] Are external dependencies mocked appropriately?
- [ ] Are database operations tested?
- [ ] Are API endpoints tested end-to-end?

### Test Quality
- [ ] Are tests testing behavior, not implementation?
- [ ] Are test names descriptive?
- [ ] Are assertions meaningful (not just "no error")?
- [ ] Are tests maintainable (not overly complex)?
- [ ] Are there test anti-patterns (testing private methods, etc.)?

### Test Infrastructure
- [ ] Are test fixtures well-organized?
- [ ] Are there test helpers for common patterns?
- [ ] Is test data setup/teardown clean?
- [ ] Are tests runnable in isolation?

### Missing Test Categories
- [ ] TODO/FIXME comments indicating missing tests?
- [ ] Placeholder test files with no tests?
- [ ] Functions with `# untested` comments?
- [ ] Complex logic without corresponding tests?

---

## Context You Need

### Your Specific Scope

**IN SCOPE:**
- Test file presence and organization
- Test coverage assessment
- Unit test quality
- Integration test presence
- Test infrastructure quality
- Missing test identification

**OUT OF SCOPE (handled by other gap categories):**
- Error handling implementation (Gap 1)
- Logging implementation (Gap 2)
- Configuration issues (Gap 4)
- Migration concerns (Gap 5)

---

## Inputs

The parent agent will provide:

| Input | Description |
|-------|-------------|
| `SCOPE_FILES` | List of implementation files |
| `TEST_FILES` | List of test files |
| `OUTPUT_FILE` | Path where you must write your findings |
| `ENTRY_POINTS` | Discovered entry points for context |

---

## Expected Output

### Output File

**YOU MUST WRITE TO:** The `OUTPUT_FILE` path provided in your spawn prompt.

### Required Format

```markdown
# Gap Analysis: Testing

**Analyzed:** {timestamp}
**Scope:** {implementation files}
**Subagent:** Gap 3 - Testing

## Summary

{2-3 sentence executive summary of testing gaps}

## Test Coverage Map

| Entry Point/Function | Test File | Coverage | Notes |
|---------------------|-----------|----------|-------|
| `{function_1}` | `{test_file}` | {FULL | PARTIAL | NONE} | {details} |
| `{function_2}` | - | NONE | No tests found |

## Gap Inventory

### Coverage Gaps

#### Gap C1: {Short Title}
- **Severity:** {P0-Critical | P1-High | P2-Medium | P3-Low}
- **Location:** `{file}:{line}` (untested code)
- **Gap Description:** {What is not tested}
- **Evidence:** {Code that has no tests}
- **Impact:** {What bugs could slip through}
- **Recommendation:** {Specific test to add}

### Unit Test Gaps

#### Gap U1: {Short Title}
...

### Integration Test Gaps

#### Gap I1: {Short Title}
...

### Test Quality Gaps

#### Gap Q1: {Short Title}
...

### Infrastructure Gaps

#### Gap F1: {Short Title}
...

### Missing Test Categories

#### Gap M1: {Short Title}
...

## Coverage Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Entry point tests | {COVERED | PARTIAL | MISSING} | {details} |
| Happy path tests | {COVERED | PARTIAL | MISSING} | {details} |
| Error path tests | {COVERED | PARTIAL | MISSING} | {details} |
| Edge case tests | {COVERED | PARTIAL | MISSING} | {details} |
| Integration tests | {COVERED | PARTIAL | MISSING} | {details} |
| Test infrastructure | {COVERED | PARTIAL | MISSING} | {details} |

## Quality Checklist

- [ ] All 6 testing aspects analyzed
- [ ] Each gap has severity, evidence, and recommendation
- [ ] No out-of-scope items analyzed
- [ ] File:line references for all gaps
- [ ] Output written to correct location
```

---

## Severity Guidelines for Testing

| Severity | Criteria |
|----------|----------|
| **P0-Critical** | Critical path completely untested |
| **P1-High** | Important functionality missing tests |
| **P2-Medium** | Edge cases or error paths not tested |
| **P3-Low** | Test quality issues or missing assertions |

---

## Search Patterns

```python
# Find test files
Glob(pattern="**/test_*.py") or Glob(pattern="**/*.test.ts")

# Find untested indicators
Grep(pattern="(TODO|FIXME).*test|# untested|@skip|@pytest.mark.skip")

# Find assertions
Grep(pattern="(assert|expect|should)")

# Find mocking patterns
Grep(pattern="(mock|Mock|patch|stub|spy)")

# Find test decorators/markers
Grep(pattern="(@test|@pytest|describe\\(|it\\()")
```

---

## Anti-Patterns to Avoid

- **Counting lines not coverage**: Focus on path coverage, not line count
- **Ignoring test quality**: A test exists != a test is good
- **Missing test isolation**: Check for shared state issues
- **Scope creep**: Don't analyze the implementation logic itself

---

**End of Testing Gap Handoff**
