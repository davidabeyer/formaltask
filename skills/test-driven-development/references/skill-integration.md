# Complementary Skills Integration

How TDD integrates with other skills for comprehensive quality workflows.

## hunting-test-antipatterns

**Relationship:** TDD prevents anti-patterns by enforcing test-first approach.

- hunting-test-antipatterns identifies violations during test writing
- Load hunting-test-antipatterns when writing tests to catch mistakes early
- Workflow: TDD enforces discipline -> hunting-test-antipatterns provides checklist

**When to combine:** Always when writing tests. Auto-load recommendation.

## systematic-debugging

**Relationship:** When bugs appear despite passing tests, indicates weak tests.

- Symptom: High coverage, low confidence
- Cause: Testing mock behavior instead of real behavior (Anti-Pattern 1)
- Load hunting-test-antipatterns to identify weak tests

**When to combine:** Bug investigation despite green tests.

## root-cause-tracing

**Relationship:** After finding root cause, TDD requires regression test first.

- Defense-in-depth validation aligns with TDD refactor phase
- root-cause-tracing finds bug source -> TDD prevents recurrence
- Write failing test demonstrating bug -> Apply fix -> Verify passes

**When to combine:** Post-bug-fix verification.

## error-debugger

**Relationship:** After error-debugger provides fix, TDD ensures fix is tested.

- Write failing test demonstrating bug
- Apply fix
- Verify test passes
- Prevents same error from recurring

**When to combine:** After receiving fix recommendations.

## Typical Integrated Workflow

```
1. RED:       Load hunting-test-antipatterns to catch test quality issues
2. GREEN:    Implement minimal solution (tdd-guard validates)
3. REFACTOR: Keep hunting-test-antipatterns loaded for quality
4. BUG:      Load root-cause-tracing -> Find source -> TDD RED
```

## Auto-Loading Recommendations

| When TDD is loaded | Consider loading |
|--------------------|------------------|
| Writing tests | hunting-test-antipatterns |
| Bug investigation | root-cause-tracing |
| Error fixing | error-debugger |
