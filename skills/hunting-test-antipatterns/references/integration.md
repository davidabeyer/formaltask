# Integration with Complementary Skills

## test-driven-development
- TDD skill provides Red-Green-Refactor cycle
- hunting-test-antipatterns identifies violations during implementation
- Use together: TDD enforces discipline, hunting-test-antipatterns catches mistakes

## systematic-debugging
- When tests pass but bugs occur - hunting-test-antipatterns identifies weak tests
- Symptom: "All tests pass" but production fails
- Cause: Testing mock behavior (Anti-Pattern 1)

## root-cause-tracing
- When test failures are unclear - hunting-test-antipatterns reveals over-mocking
- Deep mock chains make failures hard to debug
- Solution: Reduce mocks, test real behavior

## Typical Workflow

1. Start: Load **test-driven-development** (enforces TDD cycle)
2. Writing test: Load **hunting-test-antipatterns** (catch mistakes early)
3. Test passes but bug exists: Load **hunting-test-antipatterns** (identify weak test)
4. Refactor: Keep **hunting-test-antipatterns** loaded (ensure tests still test behavior)

---

# Success Metrics

## Before hunting-test-antipatterns awareness:
- Tests pass, production fails frequently
- 80% test coverage but low confidence
- Mocks in 90% of tests
- Production code has 15+ test-only methods
- Refactoring breaks 50+ tests

## After hunting-test-antipatterns discipline:
- Tests catch bugs before production
- 80% test coverage with high confidence
- Mocks only for external dependencies (<20% of tests)
- Zero test-only methods in production
- Refactoring breaks only integration tests (as expected)

## Time Investment

- Learning anti-patterns: +2 hours upfront
- Writing better tests: +10% time per test
- Debugging production issues: -80% time (catch bugs in tests)
- **Net: 60% faster overall development** (fewer production bugs)
