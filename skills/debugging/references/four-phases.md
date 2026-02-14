# The Four Phases of Systematic Debugging

## Phase 1: Root Cause Investigation

**Goal: Understand what's actually broken and why**

**Step 1.1: Read Error Messages Carefully**
- Read ENTIRE error message, not just first line
- Identify file paths and line numbers
- Note error type (SyntaxError, TypeError, etc.)
- Extract stack trace if present
- Copy exact error text for searching

**Step 1.2: Reproduce Issue Consistently**
- Document exact steps to trigger error
- Note when it works vs when it fails
- Identify patterns in failures
- Test in isolation if possible
- Verify reproduction reliability (100% failure = easier to debug)

**Step 1.3: Check Recent Changes**
- What changed immediately before failure?
- Review last 3-5 commits if available
- Check configuration changes
- Identify new dependencies or versions
- Note environment changes

**Step 1.4: Gather Evidence in Multi-Component Systems**
- Check logs from all involved components
- Trace requests across service boundaries
- Verify data at each step
- Check network calls and responses
- Validate assumptions about system state

**Step 1.5: Trace Data Flow Backward**
- Start from error location
- Work backward through call stack
- Identify where data becomes incorrect
- Find first point of deviation from expected
- This is likely the root cause

**Output of Phase 1:**
- Exact error message and location
- Reproduction steps (100% reliable)
- Recent changes that correlate with failure
- Data flow trace to point of deviation
- Initial hypothesis about root cause

---

## Phase 2: Pattern Analysis

**Goal: Find working examples and understand differences**

**Step 2.1: Locate Working Examples**
- Find similar code that works correctly
- Identify reference implementations
- Check documentation examples
- Search codebase for proven patterns
- Locate tests that cover similar scenarios

**Step 2.2: Compare Against References Completely**
- Line-by-line comparison with working code
- Check all parameters and arguments
- Verify data types match expectations
- Compare configurations
- Note even small differences

**Step 2.3: Identify Differences Systematically**
Create comparison table:

| Aspect | Working Code | Broken Code | Impact |
|--------|-------------|-------------|--------|
| Function signature | `foo(x, y)` | `foo(x)` | Missing parameter |
| Data type | `str` | `int` | Type mismatch |
| Configuration | `timeout=30` | `timeout=5` | Too short |

**Step 2.4: Understand All Dependencies**
- What libraries/packages are involved?
- Are versions compatible?
- Are dependencies initialized correctly?
- Is order of operations correct?
- Are assumptions about state valid?

**Output of Phase 2:**
- Working reference example identified
- Systematic comparison table
- List of differences found
- Dependency analysis
- Updated hypothesis based on differences

---

## Phase 3: Hypothesis and Testing

**Goal: Verify root cause with minimal tests**

**Step 3.1: Form a Single Clear Hypothesis**
- State ONE specific hypothesis about root cause
- Make it testable (not vague like "something is wrong")
- Predict what should happen if hypothesis is correct
- Identify what would disprove hypothesis

**Example hypotheses:**
- "The function fails because parameter Y is None instead of expected string"
- "The API call times out because batch size exceeds server limit of 100"
- "The function fails because parameter Y is None instead of expected string"
- "It might be a race condition or data issue" (multiple hypotheses)

**Step 3.2: Test Minimally with One Variable**
- Change ONLY ONE thing
- Use simplest possible test
- Add logging/print statements if needed
- Verify test is valid (would fail if hypothesis wrong)

**Step 3.3: Verify Results Before Continuing**
- Did test confirm hypothesis?
  - YES: Proceed to Phase 4 (Implementation)
  - NO: Return to Phase 1 (more investigation needed)
  - PARTIAL: Refine hypothesis and test again

**Step 3.4: Acknowledge Knowledge Gaps Honestly**
- "I don't know why X happens" is acceptable
- Document unknowns clearly
- Ask for help when stuck
- Don't guess or assume

**Red flags in Phase 3:**
- Testing multiple variables simultaneously
- Skipping verification of test results
- Assuming hypothesis is correct without proof
- Moving to implementation with partial confirmation

**Output of Phase 3:**
- Verified hypothesis about root cause
- Test results confirming hypothesis
- Understanding of why problem occurs
- Clear path to fix

---

## Phase 4: Implementation

**Goal: Fix root cause with test-first approach**

**Step 4.1: Create a Failing Test Case First**
- Write test that reproduces the bug
- Verify test fails with current code
- Test should pass after fix is implemented
- Follow TDD discipline even for bug fixes

**Step 4.2: Implement a Single Root-Cause Fix**
- Fix the ROOT CAUSE identified in Phase 3
- Don't add extra changes "while you're at it"
- Keep fix minimal and focused
- Document why fix addresses root cause

**Step 4.3: Verify the Solution Works**
- Run the failing test - should now pass
- Run full test suite - no regressions
- Test the original reproduction steps - should work
- Verify fix doesn't introduce new issues

**Step 4.4: If 3+ Fixes Fail**
**STOP. Question the architecture.**

After three failed fix attempts:
1. Discuss with team (don't continue alone)
2. Consider if problem is architectural
3. Evaluate if refactoring is needed
4. Question assumptions about system design
5. Don't try a fourth patch

**Why 3 is the limit:**
- First failure: Hypothesis was wrong
- Second failure: Investigation was incomplete
- Third failure: Fundamental misunderstanding of system
- Fourth+ attempts: Wasting time, need different approach

**Output of Phase 4:**
- Failing test case for the bug
- Root-cause fix implemented
- All tests passing
- Documentation of fix rationale
