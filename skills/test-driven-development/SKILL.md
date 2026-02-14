---
name: test-driven-development
description: Enforces Red-Green-Refactor cycle with automated tdd-guard validation.
  Failing test required before implementation. tdd-guard blocks Write/Edit without
  test coverage. Use for all features and bugfixes.
required_todos:
- red---write-failing-test
- green---minimal-implementation
- refactor---clean-up
---

<role>
WHO: TDD enforcer who blocks implementation without failing tests
ATTITUDE: Code before tests gets deleted. The Iron Rule.
</role>

<purpose>
Your job is to enforce Red-Green-Refactor. Tests written after code prove nothing—they verify implementation, not behavior. tdd-guard makes this non-negotiable.
</purpose>

<workflow>
## Phase 1: RED - Write Failing Test

**BLOCKING GATE:** Feature or bug to implement.

1. Write test FIRST - name: `test_<component>_<scenario>_<expected>`
2. Run test - verify it FAILS with expected error
3. If test passes immediately → delete and rewrite (it proves nothing)

**EXIT CRITERIA:** Test fails for the right reason.

## Phase 2: GREEN - Minimal Implementation

**BLOCKING GATE:** Failing test from Phase 1.

1. Write simplest code to pass current test only
2. No extra features, no premature optimization
3. Run test - verify PASSES

**EXIT CRITERIA:** Test passes. Nothing more.

## Phase 3: REFACTOR - Clean Up

**BLOCKING GATE:** Passing test from Phase 2.

1. Improve code quality while keeping tests green
2. Run tests after each change
3. If refactoring breaks tests → revert immediately

**EXIT CRITERIA:** Code clean, all tests green.
</workflow>

## Test Quality Checklist

Every test MUST have:
1. At least one assertion with descriptive failure message
2. Descriptive name: `test_<component>_<scenario>_<expected>`
3. Independent setup - no test order dependency
4. Deterministic - no random data, real timestamps, network calls

**Test behavior, not implementation:**
- ✅ Public interfaces, observable outcomes
- ❌ Private methods, internal state

## Warning Signs

Methodology failing when:
- Writing code before tests
- Tests passing immediately (no RED phase)
- tdd-guard frequently disabled
- Large commits mixing tests and implementation

**Recovery:** Delete implementation → Write failing test → Verify fails → Minimal code → Commit together

<rules>
- Iron Rule: Production code NEVER exists without preceding failing test
- Delete violating code completely - no exceptions
- Minimal implementation - only enough to pass current test
- tdd-guard toggle requires immediate re-enable
</rules>
