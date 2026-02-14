# Legacy Code Characterization Test Protocol

**Purpose:** Safe workflow for adding tests to untested legacy code without breaking existing behavior.

## The Problem

Legacy code often lacks tests, making changes risky. Adding tests after the fact is challenging because:
- You don't know what the code currently does (including bugs)
- Refactoring without tests can introduce regressions
- Writing tests for messy code is difficult
- Uncertainty about correctness paralyzes changes

## The Solution: Characterization Tests

**Characterization tests** document what code currently does, not what it should do. They capture existing behavior (bugs included) to create a safety net before making changes.

## The Four-Step Protocol

### Step 1: Characterization Tests First

Write tests documenting **current behavior** exactly as it is, even if wrong.

**Objective:** Create executable documentation of how code behaves now.

**Example:**
```python
def test_legacy_validator_current_behavior():
    """
    CHARACTERIZATION TEST - Documents current (buggy) behavior.
    TODO: Fix bug where validator accepts emails without '@' symbol

    This test will PASS with current implementation.
    After fixing the bug, this test should FAIL (expected).
    """
    validator = LegacyUserValidator()

    # Current behavior (even though it's wrong)
    assert validator.is_valid_email("userexample.com") is True  # BUG: Missing @
    assert validator.is_valid_email("user@example.com") is True
    assert validator.is_valid_email("") is False
```

**Key points:**
- Test passes with current code (documents actual behavior)
- Docstring explicitly marks as characterization test
- Document known bugs inline with comments
- Add TODO for future fix

**Run characterization tests:**
```bash
pytest tests/test_legacy_validator.py -v
# Expected: All tests PASS (documenting current state)
```

### Step 2: Refactor to Make Testable

Make code easier to test WITHOUT changing behavior. Tests should still pass.

**Common refactorings:**
- Extract dependencies for mocking
- Break apart large functions
- Expose internal state for testing (temporary)
- Add seams for dependency injection

**Example:**
```python
# Before: Hard to test (reads real file, uses real time)
class LegacyProcessor:
    def process(self, filename):
        with open(filename) as f:  # File I/O hard to test
            data = f.read()
        timestamp = time.time()  # Non-deterministic
        return self._transform(data, timestamp)

# After: Testable (dependencies injected)
class LegacyProcessor:
    def __init__(self, file_reader=None, time_provider=None):
        self.file_reader = file_reader or self._default_file_reader
        self.time_provider = time_provider or time.time

    def process(self, filename):
        data = self.file_reader(filename)
        timestamp = self.time_provider()
        return self._transform(data, timestamp)

    def _default_file_reader(self, filename):
        with open(filename) as f:
            return f.read()
```

**Run tests after refactoring:**
```bash
pytest tests/test_legacy_validator.py -v
# Expected: All tests still PASS (same behavior)
```

**If tests fail after refactoring:**
- You changed behavior unintentionally
- Revert the refactoring
- Try smaller, safer refactoring steps

### Step 3: Feature Tests (Desired Behavior)

Write NEW tests describing correct behavior you want to implement.

**Objective:** Define expected behavior as failing tests (TDD RED phase).

**Example:**
```python
def test_validator_rejects_email_without_at_symbol():
    """
    FEATURE TEST - Defines desired behavior.
    This test currently FAILS (expected).
    After fixing the bug, this test should PASS.
    """
    validator = LegacyUserValidator()

    # Desired behavior (currently broken)
    assert validator.is_valid_email("userexample.com") is False  # Should reject
    assert validator.is_valid_email("user@example.com") is True   # Should accept

def test_validator_rejects_email_with_multiple_at_symbols():
    """FEATURE TEST - Additional validation rule"""
    validator = LegacyUserValidator()

    assert validator.is_valid_email("user@@example.com") is False
    assert validator.is_valid_email("user@host@example.com") is False
```

**Run feature tests:**
```bash
pytest tests/test_legacy_validator.py::test_validator_rejects_email_without_at_symbol -v
# Expected: FAIL (desired behavior not implemented yet)
```

**Test suite state after Step 3:**
- Characterization tests: PASS (current behavior)
- Feature tests: FAIL (desired behavior)
- This is expected and correct!

### Step 4: Implement Fix

Modify implementation to make feature tests pass.

**Example:**
```python
class LegacyUserValidator:
    def is_valid_email(self, email):
        # Old broken implementation (characterization tests documented this):
        # return len(email) > 0 and "." in email

        # New correct implementation:
        if not email or len(email) == 0:
            return False

        # Must have exactly one @ symbol
        at_count = email.count('@')
        if at_count != 1:
            return False

        # Must have domain after @
        parts = email.split('@')
        if len(parts[1]) == 0:
            return False

        return True
```

**Run full test suite:**
```bash
pytest tests/test_legacy_validator.py -v

# Expected results:
# ✗ test_legacy_validator_current_behavior FAILED (characterization test now fails - expected)
# ✓ test_validator_rejects_email_without_at_symbol PASSED (feature test now passes)
# ✓ test_validator_rejects_email_with_multiple_at_symbols PASSED
```

**Handle failing characterization tests:**

Option 1: Update characterization test to document new behavior
```python
def test_legacy_validator_current_behavior():
    """
    UPDATED CHARACTERIZATION TEST - Now documents fixed behavior.
    Bug was fixed in commit abc123.
    """
    validator = LegacyUserValidator()

    # Fixed behavior
    assert validator.is_valid_email("userexample.com") is False  # FIXED: Now rejects
    assert validator.is_valid_email("user@example.com") is True
```

Option 2: Delete characterization test (no longer needed)
```bash
# Feature tests now document correct behavior
rm tests/test_legacy_validator_characterization.py
```

## Complete Example Workflow

```python
# ==================== STEP 1: Characterization Tests ====================
# File: tests/test_legacy_cart.py

def test_legacy_cart_current_behavior():
    """
    CHARACTERIZATION TEST - Documents current behavior.

    Known bugs:
    - Negative quantities allowed (should reject)
    - Total calculation incorrect for > 10 items (off by one)
    """
    cart = LegacyShoppingCart()

    # Current behavior (bugs included)
    cart.add_item("apple", quantity=-5)  # BUG: Negative allowed
    assert cart.item_count() == -5  # Current (wrong) behavior

    # Add 11 items
    for i in range(11):
        cart.add_item(f"item_{i}", quantity=1)

    assert cart.total() == 10  # BUG: Off by one for >10 items

# ==================== STEP 2: Refactor ====================
# File: legacy_cart.py (refactored for testability)

class LegacyShoppingCart:
    def __init__(self, validator=None):
        self.items = []
        self.validator = validator or self._default_validator

    def add_item(self, name, quantity):
        # Extracted validation (can now mock in tests)
        if self.validator.is_valid_quantity(quantity):
            self.items.append({'name': name, 'quantity': quantity})

    def _default_validator(self):
        return ItemValidator()

# Tests still pass after refactoring (behavior unchanged)

# ==================== STEP 3: Feature Tests ====================
# File: tests/test_cart_features.py

def test_cart_rejects_negative_quantities():
    """FEATURE TEST - Negative quantities should be rejected"""
    cart = LegacyShoppingCart()
    cart.add_item("apple", quantity=-5)

    assert cart.item_count() == 0  # Should reject, not add

def test_cart_total_correct_for_many_items():
    """FEATURE TEST - Total should count all items"""
    cart = LegacyShoppingCart()

    for i in range(11):
        cart.add_item(f"item_{i}", quantity=1)

    assert cart.total() == 11  # Should count all 11 items

# Feature tests FAIL (expected - behavior not fixed yet)

# ==================== STEP 4: Implement Fix ====================
# File: legacy_cart.py (with fixes)

class LegacyShoppingCart:
    def add_item(self, name, quantity):
        if quantity < 0:  # FIX: Reject negative quantities
            return
        self.items.append({'name': name, 'quantity': quantity})

    def total(self):
        # FIX: Correct counting for all items
        return sum(item['quantity'] for item in self.items)

# Run tests:
# ✗ Characterization test fails (expected - documents old bugs)
# ✓ Feature tests pass (fixes implemented)
```

## Rules

**❌ NEVER:**
- Add features to untested legacy code
- Refactor without characterization tests first
- Fix bugs before documenting current behavior
- Change behavior during Step 2 (refactoring)

**✅ ALWAYS:**
- Write characterization tests FIRST
- Document known bugs in test docstrings
- Verify characterization tests PASS with current code
- Verify feature tests FAIL before implementing
- Run full test suite after each step

## TDD Guard Integration

TDD Guard enforces this protocol:

**Step 1:** Characterization tests allow Write/Edit operations
- test.json shows tests exist and pass
- PreToolUse hook allows operation

**Step 2:** Refactoring allowed if tests stay green
- test.json updated after each change
- If tests fail, tdd-guard blocks further changes

**Step 3:** Feature tests (failing) block implementation
- Writing implementation without failing test → BLOCKED
- Must write feature test first (RED phase)

**Step 4:** Implementation allowed after feature tests exist
- test.json shows new tests (even if failing)
- tdd-guard allows Write/Edit for implementation

## Common Patterns

### Pattern: API Exploration

When you don't know what legacy code does, write characterization tests that explore:

```python
def test_explore_legacy_parser_behavior():
    """Characterization: What does parser actually return?"""
    parser = LegacyParser()

    # Try various inputs to discover behavior
    assert parser.parse("") == ???  # Run test, see what it returns
    assert parser.parse("foo") == ???
    assert parser.parse("foo=bar") == ???

    # Fill in actual results, documenting discovered behavior
```

### Pattern: Regression Prevention

Characterization tests prevent regressions during refactoring:

```python
# Before refactoring: Capture ALL current behavior
def test_legacy_processor_edge_cases():
    """Characterization: Edge cases found in production logs"""
    processor = LegacyProcessor()

    # Real edge cases from production
    assert processor.handle(None) == None  # Doesn't crash on None
    assert processor.handle("") == ""      # Empty string handled
    assert processor.handle("€100") == "100"  # Currency symbols stripped
```

Now when refactoring, tests ensure you don't break these edge cases.

### Pattern: Incremental Migration

Large legacy systems can be migrated incrementally:

**Phase 1:** Characterization tests for module A
**Phase 2:** Refactor module A (tests green)
**Phase 3:** Feature tests + fixes for module A
**Phase 4:** Repeat for module B

Each phase is safe because previous modules have test coverage.

## Troubleshooting

### "I can't write characterization tests - code is too complex"

**Solution:** Start with highest-level interface:
```python
# Don't characterize internals, characterize public API
def test_legacy_system_api():
    """Characterization: Public API behavior"""
    system = LegacySystem()

    # What does main entry point return?
    result = system.process_request({"user": "alice"})
    assert result["status"] == "success"  # Document actual return value
```

### "Characterization tests fail - I can't run legacy code"

**Solution:** Mock problematic dependencies:
```python
def test_legacy_with_mocked_database(mocker):
    """Characterization: With database mocked"""
    mock_db = mocker.patch('legacy.database')
    mock_db.query.return_value = [{"id": 1, "name": "test"}]

    system = LegacySystem()
    result = system.get_users()

    # Document behavior with mocked database
    assert result == [{"id": 1, "name": "test"}]
```

### "Characterization tests document bugs - should I fix them?"

**Not in Step 1!** Document bugs, fix in Step 4:
```python
def test_legacy_current_behavior_with_known_bug():
    """
    Characterization: Current behavior includes XSS vulnerability.
    TODO (Step 4): Fix XSS vulnerability in output escaping

    Security issue tracked in: JIRA-1234
    """
    processor = LegacyHtmlProcessor()

    # SECURITY BUG: Doesn't escape HTML
    assert processor.format("<script>alert('xss')</script>") == "<script>alert('xss')</script>"
```

Then in Step 3, write feature test for correct behavior.

### "Step 2 refactoring broke characterization tests"

You changed behavior during refactoring (violates protocol):
1. Revert refactoring
2. Re-read Step 2 rules
3. Try smaller refactoring that preserves behavior
4. Run tests after each small change

## When to Use This Protocol

**Use characterization tests for:**
- Legacy code with no tests
- Code you don't understand
- Code with unknown behavior
- Code you're afraid to change
- Third-party code you need to modify

**Don't use for:**
- Greenfield projects (regular TDD instead)
- Well-tested code (add feature tests directly)
- Throwaway prototypes

## See Also

- TDD Guard System Analysis: `~/formaltask/Memory/Projects/Gitbutler/Reference/TDD-Guard-System-Analysis.md`
- Test Quality Rules: `references/test-quality-rules.md`
- Main TDD Workflow: `SKILL.md`
