# TDD as Prevention

**All five anti-patterns share a root cause: Implementation before tests.**

Test-Driven Development prevents these issues by forcing developers to:
1. **Write failing test first** - Ensures test verifies real behavior (can't test mocks that don't exist yet)
2. **Watch test fail** - Proves test is actually testing something (not always passing)
3. **Write minimal implementation** - Prevents over-mocking (no dependencies to mock yet)
4. **See test pass** - Validates behavior works
5. **Refactor** - Tests ensure behavior unchanged

## How TDD Prevents Each Anti-Pattern

| Anti-Pattern | How TDD Prevents It |
|--------------|---------------------|
| Testing mock behavior | Can't mock what doesn't exist - test must verify real behavior first |
| Test-only methods | No production code exists yet - can't add test methods to it |
| Blind mocking | No dependencies exist yet - must understand what to implement |
| Incomplete mocks | Test fails if mock is incomplete - forces complete contracts |
| Deferred testing | Tests come first - can't defer what's already done |

## Integration with tdd-guard

Your tdd-guard setup enforces TDD discipline through technical blocking:

**PreToolUse Hook:**
```python
# tdd-guard blocks Write/Edit operations without test coverage
if tool in ['Write', 'Edit'] and is_implementation_file(file_path):
    if not has_test_coverage(file_path):
        return {"reason": "No test found. Write test first (TDD RED phase)"}
```

**This prevents:**
- Implementation before tests (Anti-Pattern 5)
- Test-only methods (no production code exists yet)
- Blind mocking (must understand interface to write test)

## Workflow Example

```bash
# 1. Write test first (RED)
# tdd-guard: Allows test file creation
vim tests/test_discount.py

# 2. Run test -> fails
pytest tests/test_discount.py  # FAIL: module not found

# 3. Write implementation (GREEN)
# tdd-guard: Allows implementation AFTER test exists
vim app/discount.py

# 4. Run test -> passes
pytest tests/test_discount.py  # PASS: 3/3 tests

# 5. Refactor
# tdd-guard: Allows refactoring (tests already exist)
vim app/discount.py  # Extract TIER_DISCOUNTS dict
pytest tests/test_discount.py  # PASS: still 3/3
```
