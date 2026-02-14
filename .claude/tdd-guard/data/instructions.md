# Custom TDD Guard Instructions for claude-code Project

## Purpose

These instructions guide the AI validator (Claude Sonnet 4) in assessing test quality beyond basic TDD cycle enforcement. The validator interprets these rules in natural language to identify test quality issues, anti-patterns, and project-specific violations.

## Core Test Quality Requirements

### Assertions

**Every test MUST contain at least one meaningful assertion.**

- Tests without assertions are not tests - they only verify that code runs without crashing
- Use descriptive assertion messages that explain what failed and why
- Avoid empty test bodies, pass-only tests, or tests that only print output
- Each assertion should verify a specific aspect of the expected behavior

**Good examples:**
```python
def test_user_creation_sets_default_role():
    user = create_user("alice")
    assert user.role == "member", "New users should default to member role"

def test_divide_by_zero_raises_error():
    with pytest.raises(ZeroDivisionError, match="division by zero"):
        calculator.divide(10, 0)
```

**Bad examples:**
```python
def test_user_creation():
    create_user("alice")  # No assertion - just checks it doesn't crash

def test_database_query():
    result = db.query("SELECT * FROM users")
    print(result)  # Printing is not testing
```

### Test Naming

**Test names MUST describe WHAT behavior is tested, not HOW it's implemented.**

- Format: `test_<component>_<scenario>_<expected_outcome>`
- Names should read like a specification of behavior
- Avoid implementation details in test names
- Be specific enough that failures are self-documenting

**Good examples:**
```python
test_login_invalid_password_returns_401()
test_cache_expired_entry_fetches_fresh_data()
test_validator_empty_email_rejects_input()
test_parser_malformed_json_raises_parse_error()
```

**Bad examples:**
```python
test_function_1()  # No behavior described
test_check_if_works()  # Too vague
test_calls_database_method()  # Tests HOW, not WHAT
test_loop_iteration()  # Implementation detail, not behavior
```

### Test Independence and Isolation

**Tests MUST be completely independent and NOT depend on execution order.**

- Each test must set up its own fixtures and data
- Tests must not share mutable state
- Tests must clean up after themselves (or use fixtures that do)
- Tests must be runnable in any order, individually or as a suite
- Use pytest fixtures for shared setup, never global variables

**Good examples:**
```python
@pytest.fixture
def temp_database():
    db = create_test_database()
    yield db
    db.cleanup()

def test_user_insertion(temp_database):
    temp_database.insert_user("alice")
    assert temp_database.count_users() == 1
```

**Bad examples:**
```python
# Global state shared between tests
USERS = []

def test_add_user():
    USERS.append("alice")
    assert len(USERS) == 1

def test_remove_user():  # Depends on test_add_user running first!
    USERS.remove("alice")
    assert len(USERS) == 0
```

### Determinism

**Tests MUST produce the same results every time they run.**

- No random data generation without fixed seeds
- No timestamp dependencies (mock datetime/time functions)
- No network calls (mock external APIs and services)
- No file system dependencies on non-test files
- No reliance on system state (environment variables, current directory, etc.)

**Good examples:**
```python
def test_password_hashing_is_consistent(mocker):
    mocker.patch('random.randint', return_value=12345)
    hash1 = hash_password("secret")
    hash2 = hash_password("secret")
    assert hash1 == hash2

def test_scheduled_task_runs_at_midnight(mocker):
    mock_time = mocker.patch('datetime.datetime')
    mock_time.now.return_value = datetime(2024, 1, 1, 0, 0, 0)
    assert scheduler.should_run_task() is True
```

**Bad examples:**
```python
def test_random_selection():
    item = random.choice([1, 2, 3, 4, 5])  # Non-deterministic!
    assert item in [1, 2, 3, 4, 5]

def test_cache_expiry():
    cache.set("key", "value", ttl=1)
    time.sleep(2)  # Timing-dependent test
    assert cache.get("key") is None
```

### Behavioral Testing (Black Box Approach)

**Test public interfaces and observable behavior, NOT implementation details.**

- Focus on inputs, outputs, and side effects
- Avoid testing private methods directly
- Don't assert on internal state unless it's part of the public contract
- Tests should survive refactoring if behavior stays the same

**Good examples:**
```python
def test_shopping_cart_total_calculation():
    cart = ShoppingCart()
    cart.add_item("apple", price=1.50, quantity=3)
    cart.add_item("banana", price=0.75, quantity=2)
    assert cart.get_total() == 6.00  # Public interface

def test_user_registration_sends_welcome_email(mocker):
    mock_mailer = mocker.patch('app.mailer.send')
    register_user("alice@example.com")
    mock_mailer.assert_called_once()  # Observable side effect
```

**Bad examples:**
```python
def test_internal_cache_structure():
    cache = Cache()
    cache.set("key", "value")
    assert cache._internal_dict["key"] == "value"  # Testing private implementation

def test_algorithm_uses_specific_sorting_method():
    sorter = DataSorter()
    sorter.sort([3, 1, 2])
    assert sorter._used_quicksort is True  # Testing HOW, not WHAT
```

## TypeScript TDD Workflow

**TypeScript compilation errors are part of the TDD red phase.**

When writing new functionality in TypeScript/JavaScript projects, TDD follows a two-phase red cycle:

### Red Phase 1: TypeScript Compilation Failure (EXPECTED)

When you write a test that calls a non-existent function or property:

```typescript
// Test file
test('returns main worktree path from any worktree', () => {
  const mainPath = epic.getMainWorktreePath();  // TS2339: Property does not exist
  expect(mainPath).toBeTruthy();
});
```

**Expected errors:**
- `TS2339`: Property does not exist on type
- `TS2304`: Cannot find name
- `TS2345`: Argument of type X is not assignable to parameter of type Y

**Valid action: Add stub export**

```typescript
// Implementation file
export function getMainWorktreePath(): string {
  throw new Error('Not implemented');
}
```

**This is NOT cheating.** This is canonical TDD in statically-typed languages. The stub:
- Makes TypeScript compilation pass (moves to Red Phase 2)
- Explicitly declares the function exists but does nothing yet
- Is equivalent to the `NameError` you'd get in Python
- Is NOT solving the problem (it throws immediately)

### Red Phase 2: Runtime Test Failure (REQUIRED)

After adding the stub, run tests:

```bash
npm test
# ✗ Test fails with: Error: Not implemented
```

**This is the true RED phase** - your test runs and fails with expected behavior.

**Valid action: Implement real function**

Now write the actual implementation to make the test pass.

### Green Phase: Test Passes

```typescript
export function getMainWorktreePath(): string {
  const output = execSync('git worktree list --porcelain', {encoding: 'utf-8'});
  // ... actual implementation
  return mainWorktreePath;
}
```

Test passes ✓

### Why This Matters

**Dynamic languages (Python):**
```python
def test_login():
    result = authenticate_user("alice", "pass")  # Function doesn't exist
    assert result is True

# Run test → NameError (this is RED)
```

**Static languages (TypeScript):**
```typescript
test('login', () => {
  const result = authenticateUser("alice", "pass");  // TS2304
  expect(result).toBe(true);
});

// Can't run test yet - TypeScript blocks it
// Must add stub FIRST to get to runtime failure
```

### Validation Rules

**ALLOW stub implementations when:**
- Test file exists with test calling non-existent function
- TypeScript compilation fails with TS2339, TS2304, TS2345
- Stub only throws `Error('Not implemented')` or similar
- No business logic in stub

**BLOCK full implementations when:**
- test.json doesn't show a runtime failure yet
- Skipping from TypeScript error directly to implementation
- No test execution evidence (test.json missing)

**Example stub patterns (ALL VALID):**
```typescript
export function foo(): string {
  throw new Error('Not implemented');
}

export function bar(): number {
  throw new Error('TODO');
}

export function baz(): void {
  throw new Error('Not yet implemented');
}
```

**Example cheating patterns (INVALID):**
```typescript
export function foo(): string {
  return "hardcoded value";  // ❌ Solving problem without test failure
}

export function bar(): number {
  return 42;  // ❌ Implementation before runtime failure
}

export function baz(): void {
  console.log("doing work");  // ❌ Business logic in stub
}
```

### Reference

This workflow is from Kent Beck's "Test-Driven Development by Example" and is standard practice in statically-typed languages. The stub step is NOT a workaround - it's how TDD works with compile-time type checking.

## Python New Module Creation

**ModuleNotFoundError and ImportError for new modules ARE valid failing tests.**

When creating a new Python module, the TDD cycle works like this:

### Red Phase: Import Failure (VALID)

When you write a test that imports a non-existent module:

```python
# Test file
def test_task_status_open_exists():
    from hooks.lib.constants import TaskStatus  # ModuleNotFoundError!
    assert TaskStatus.OPEN == "open"
```

**Expected errors:**
- `ModuleNotFoundError: No module named 'hooks.lib.constants'`
- `ImportError: cannot import name 'TaskStatus' from 'hooks.lib.constants'`

**These ARE valid "failing for the right reason"** because:
- The test clearly specifies what module/class should exist
- The fix is to create the module with the required exports
- This is identical to TypeScript's TS2304 "Cannot find name" errors

### Green Phase: Create Module

**Valid action: Create the module with minimal implementation**

```python
# hooks/lib/constants.py
from enum import StrEnum

class TaskStatus(StrEnum):
    OPEN = "open"
```

### Why This is Valid TDD

1. The test defines the **contract** (what should exist)
2. The import error is the **feedback** (it doesn't exist yet)
3. Creating the module is the **minimal implementation** to pass

**This is NOT premature implementation** - it's the correct TDD response to a failing import.

### Validation Rules

**ALLOW module creation when:**
- Test file exists that imports from the new module
- Test fails with `ModuleNotFoundError` or `ImportError`
- Implementation only includes what the test imports/uses

**BLOCK module creation when:**
- No test imports from the module yet
- Adding functionality beyond what tests require
- No evidence of test execution (test.json missing/stale)

### Bash/BATS Function Tests

For bash scripts tested with BATS, grep-based existence tests ARE valid TDD:

```bash
@test "session_exists function is defined in script" {
    grep -q 'session_exists()' "$SCRIPT"
}
```

**ALLOW bash function implementation when:**
- BATS test uses `grep -q 'function_name()'` to check function exists
- Test fails because function is not defined yet
- test.json shows the BATS test with state "failed"

This is valid because:
1. Bash has no "import" mechanism like Python
2. grep for function definition IS the correct way to test function existence
3. The test will pass once the function is added

## Project-Specific Rules

### MCP Server Tests

**All MCP server API endpoints MUST have comprehensive test coverage.**

- Every endpoint must have tests for both success and error cases
- Test all HTTP status codes the endpoint can return (200, 400, 401, 404, 500, etc.)
- Test request validation (missing fields, invalid types, boundary cases)
- Test response structure and data types

**Database operations in MCP servers:**
- MUST use transactions with automatic rollback in tests
- MUST use test database fixtures, never production data
- MUST test constraint violations (unique, foreign key, etc.)
- MUST test query edge cases (empty results, large result sets)

**External API calls in MCP servers:**
- MUST be mocked - never make real network calls in tests
- MUST test both successful responses and error responses
- MUST test timeout handling and retry logic
- MUST test API rate limiting behavior

**Good example:**
```python
@pytest.fixture
def test_db():
    db = create_test_database()
    yield db
    db.rollback_all()

def test_create_user_endpoint_success(test_db, client):
    response = client.post("/users", json={"name": "alice", "email": "alice@example.com"})
    assert response.status_code == 201
    assert response.json()["name"] == "alice"

def test_create_user_endpoint_duplicate_email(test_db, client):
    client.post("/users", json={"name": "alice", "email": "alice@example.com"})
    response = client.post("/users", json={"name": "bob", "email": "alice@example.com"})
    assert response.status_code == 409
    assert "email already exists" in response.json()["error"]
```

### Hook Tests

**All bash hooks MUST have integration tests in the hooks/tests/ directory.**

- Test both success and failure scenarios
- Verify correct exit codes (0 for success, non-zero for errors)
- Verify output messages to stdout/stderr
- Test with realistic file system state
- Test error handling and edge cases

**Good example for a pre-commit hook test:**
```bash
#!/usr/bin/env bats

@test "pre-commit hook passes for valid Python files" {
    # Setup
    echo "def hello(): return 'world'" > test_file.py

    # Execute
    run ../hooks/pre-commit.sh

    # Verify
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All checks passed" ]]
}

@test "pre-commit hook fails for Python syntax errors" {
    # Setup
    echo "def hello( return 'world'" > test_file.py

    # Execute
    run ../hooks/pre-commit.sh

    # Verify
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Syntax error" ]]
}
```

### Claude Code Integration Tests

**Tests involving Claude Code features (skills, commands, agents) have special requirements:**

- Mock Claude API calls - never make real API requests in tests
- Test command parsing and validation logic independently
- Test file operations with temporary directories
- Verify configuration loading and validation
- Test error messages and user-facing output

## Anti-Patterns to Avoid

### The Mockery (Excessive Mocking)

**Avoid excessive mocking (more than 3 mocks per test is a warning sign).**

Why it's bad:
- Tests become tightly coupled to implementation details
- Refactoring breaks tests even when behavior doesn't change
- Tests become harder to read and maintain than the code they test

What to do instead:
- Mock external dependencies (APIs, databases, file system)
- Don't mock internal collaborators in the same module
- If you need many mocks, consider whether the code needs refactoring
- Use real objects for simple collaborators

**Bad example:**
```python
def test_user_service_create_user(mocker):
    mock_validator = mocker.Mock()
    mock_hasher = mocker.Mock()
    mock_db = mocker.Mock()
    mock_logger = mocker.Mock()
    mock_mailer = mocker.Mock()
    mock_cache = mocker.Mock()
    # This test is testing mock interactions, not real behavior!
```

**Better approach:**
```python
def test_user_service_create_user(test_db, mocker):
    # Only mock external dependencies
    mock_mailer = mocker.patch('app.mailer.send')

    # Use real validator, hasher, logger (internal collaborators)
    user = user_service.create_user("alice", "alice@example.com", "password123")

    assert user.name == "alice"
    assert test_db.get_user(user.id) is not None
    mock_mailer.assert_called_once()
```

### The Giant (Overly Long Tests)

**Keep tests under 20 lines. One test = one behavior.**

Why it's bad:
- Long tests are hard to understand
- Multiple behaviors in one test make failures ambiguous
- Setup complexity suggests design problems

What to do instead:
- Split complex scenarios into multiple focused tests
- Use fixtures for complex setup
- Test one behavior per test function

**Bad example:**
```python
def test_user_workflow():
    # 50 lines of setup
    user = create_user(...)
    user.verify_email()
    user.update_profile(...)
    user.change_password(...)
    # 20 lines of assertions testing multiple behaviors
```

**Better approach:**
```python
def test_user_email_verification_marks_account_active():
    user = create_unverified_user()
    user.verify_email()
    assert user.is_active is True

def test_user_profile_update_changes_display_name():
    user = create_user()
    user.update_profile(display_name="Alice Smith")
    assert user.display_name == "Alice Smith"
```

### Excessive Setup (Complex Test Initialization)

**Test setup should be less than 5 lines per test.**

Why it's bad:
- Complex setup obscures what's being tested
- Suggests the code under test has too many dependencies
- Makes tests brittle and hard to maintain

What to do instead:
- Move complex setup to pytest fixtures
- Use factory functions or builder patterns for test data
- Consider whether code needs refactoring if setup is complex

**Bad example:**
```python
def test_order_processing():
    # 15 lines of setup
    db = Database()
    db.connect()
    user = User(name="alice", email="alice@example.com", role="customer")
    db.save(user)
    product1 = Product(name="Widget", price=10.0, stock=100)
    product2 = Product(name="Gadget", price=20.0, stock=50)
    db.save(product1)
    db.save(product2)
    cart = ShoppingCart(user=user)
    cart.add_item(product1, quantity=2)
    cart.add_item(product2, quantity=1)

    # Finally, the actual test
    order = process_order(cart)
    assert order.total == 40.0
```

**Better approach:**
```python
@pytest.fixture
def customer_with_cart(test_db):
    user = create_test_user("alice")
    cart = create_test_cart(user, items=[
        ("Widget", 10.0, 2),
        ("Gadget", 20.0, 1)
    ])
    return user, cart

def test_order_processing_calculates_correct_total(customer_with_cart):
    user, cart = customer_with_cart
    order = process_order(cart)
    assert order.total == 40.0
```

### The Liar (Tests That Don't Test What They Claim)

**Test names and assertions must accurately reflect what's being tested.**

Why it's bad:
- Misleading tests waste debugging time
- False confidence in test coverage
- Makes test maintenance confusing

**Bad example:**
```python
def test_user_authentication_validates_password():
    user = User(name="alice", password_hash="xyz123")
    assert user.name == "alice"  # Not testing password validation at all!
```

**Good example:**
```python
def test_user_authentication_rejects_incorrect_password():
    user = User(name="alice", password="correct_password")
    result = user.authenticate("wrong_password")
    assert result is False
```

### The Inspector (Testing Private Methods)

**Do not write tests that directly call private methods (methods starting with _ in Python).**

Why it's bad:
- Private methods are implementation details
- Tests break when refactoring internal structure
- Couples tests to implementation rather than behavior

What to do instead:
- Test private methods indirectly through public interfaces
- If a private method is complex enough to need testing, it might need to be extracted to its own class

**Bad example:**
```python
def test_internal_cache_update():
    cache = Cache()
    cache._update_internal_index("key", "value")  # Testing private method
    assert cache._index["key"] == "value"
```

**Good example:**
```python
def test_cache_retrieval_returns_stored_value():
    cache = Cache()
    cache.set("key", "value")  # Public interface
    assert cache.get("key") == "value"  # Public interface
```

## Validation Approach

When reviewing tests, the AI validator should:

1. **Check for assertion presence** - Flag any test without assertions
2. **Evaluate test naming** - Flag vague or implementation-focused names
3. **Assess independence** - Look for shared state or order dependencies
4. **Verify determinism** - Flag random, time-based, or network-dependent tests
5. **Check behavioral focus** - Flag tests of private methods or internal state
6. **Project-specific checks** - Apply MCP server and hook testing requirements
7. **Anti-pattern detection** - Flag mockery, giants, excessive setup, liars, inspectors

For each violation found, provide:
- **Clear description** of the problem
- **Specific line numbers** where the issue occurs
- **Actionable suggestion** for how to fix it
- **Severity level** (blocking, warning, or suggestion)

## Starting Philosophy

These rules start permissive and will be tightened based on real-world usage:
- Focus on clear violations rather than style preferences
- Provide helpful explanations, not just "this is wrong"
- Allow flexibility for edge cases and special situations
- Update these instructions based on false positives and new patterns discovered

The goal is to catch real quality issues while minimizing friction in the development workflow.
