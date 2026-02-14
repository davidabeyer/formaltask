# Red-Green-Refactor Cycle (Detailed)

The TDD cycle with code examples and verification steps.

## RED: Write Failing Test

Write test FIRST before any implementation exists. Use descriptive names: `test_<component>_<scenario>_<expected_outcome>`.

### Minimal Example

```python
def test_calculator_add_returns_sum():
    """Verify add() sums two integers"""
    assert add(2, 3) == 5, "Should return 5 when adding 2+3"
```

### Run and Verify Failure

```bash
pytest tests/test_calculator.py -v
# Expected: ImportError or AssertionError
```

**If test passes immediately, it proves nothing. Delete and rewrite.**

### Failure Message Requirements

The failure message should indicate:
- What behavior was expected
- What actually happened
- Enough context to debug without reading implementation

## GREEN: Write Minimal Implementation

Write simplest possible code to pass current test only. No premature optimization or extra features.

```python
def add(a, b):
    return a + b  # Minimal - nothing more
```

### Run and Verify Pass

```bash
pytest tests/test_calculator.py -v
# Expected: test_calculator_add_returns_sum PASSED
```

### Common Mistakes in GREEN Phase

- Adding features not required by current test
- Optimizing before tests pass
- Writing "complete" implementation instead of minimal
- Ignoring edge cases (add tests for those first)

## REFACTOR: Clean Up

Improve code quality while keeping tests green. Run tests after each change.

### Refactoring Opportunities

- Extract duplicate code into functions
- Rename variables for clarity
- Simplify conditional logic
- Remove dead code
- Improve error messages

### Refactor Safety Rules

1. **All tests must remain green**
2. If refactoring breaks tests, revert immediately
3. Make small, incremental changes
4. Run tests after each change
5. Don't add new behavior during refactor

## Complete Cycle Example

### Step 1: RED - Write Failing Test

```python
# tests/test_user.py
def test_user_full_name_combines_first_and_last():
    user = User(first_name="John", last_name="Doe")
    assert user.full_name == "John Doe"
```

Run: `pytest tests/test_user.py -v` -> NameError: User not defined

### Step 2: GREEN - Minimal Implementation

```python
# src/user.py
class User:
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
```

Run: `pytest tests/test_user.py -v` -> PASSED

### Step 3: REFACTOR - Improve Quality

No refactoring needed for this simple case. Move to next test.

### Step 4: Next Cycle - Handle Edge Cases

```python
def test_user_full_name_handles_missing_last_name():
    user = User(first_name="Madonna", last_name="")
    assert user.full_name == "Madonna"
```

Run -> FAILS -> Add handling -> PASSES -> Repeat
