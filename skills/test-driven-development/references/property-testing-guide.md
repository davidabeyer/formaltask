# Property-Based Testing with Hypothesis

**Integration:** TDD Guard + Hypothesis for comprehensive test coverage

Property-based testing discovers edge cases by generating hundreds of test inputs automatically. Use alongside example-based tests for maximum coverage.

## When to Use Property Testing

**Ideal for:**
1. **Data transformations** - Parsers, serializers, normalizers, formatters
2. **Validation logic** - Input validators, type checkers, constraint verifiers
3. **Algorithms** - Sorting, filtering, searching, aggregating
4. **Codecs** - Encode/decode pairs, compression, encryption
5. **Pure utilities** - Path manipulation, string processing, math functions

**Not ideal for:**
- UI code (too stateful)
- External API calls (mock in example tests instead)
- Database operations (use integration tests)
- One-off scripts or throwaway code

## TDD Workflow with Property Tests

### Phase 1: Example Test First (RED)

Start with 1-2 example tests demonstrating specific behaviors:

```python
# tests/test_normalizer.py
def test_normalize_removes_double_slashes():
    """Specific example: double slashes should be collapsed"""
    assert normalize_path("a//b") == "a/b"

def test_normalize_removes_trailing_slash():
    """Specific example: trailing slash should be removed"""
    assert normalize_path("a/b/") == "a/b"
```

**Run and verify failure:**
```bash
pytest tests/test_normalizer.py -v
# Expected: ImportError or AssertionError (no implementation yet)
```

### Phase 2: Minimal Implementation (GREEN)

Write simplest code to pass example tests:

```python
# normalizer.py
def normalize_path(path):
    # Minimal implementation
    path = path.replace("//", "/")
    if path.endswith("/"):
        path = path[:-1]
    return path
```

**Run and verify pass:**
```bash
pytest tests/test_normalizer.py -v
# Expected: Both tests PASSED
```

### Phase 3: Generate Property Tests (REFACTOR)

Use `/property-test` command to generate property-based tests:

```bash
/property-test normalizer.py
```

This generates `tests/test_normalizer_properties.py` with hypothesis tests:

```python
from hypothesis import given
import hypothesis.strategies as st

@given(st.text())
def test_normalize_is_idempotent(path):
    """Property: Normalizing twice produces same result"""
    normalized = normalize_path(path)
    assert normalize_path(normalized) == normalized

@given(st.text())
def test_normalize_never_contains_double_slash(path):
    """Property: Output never has double slashes"""
    result = normalize_path(path)
    assert "//" not in result

@given(st.text())
def test_normalize_never_ends_with_slash(path):
    """Property: Output never ends with slash (except root)"""
    result = normalize_path(path)
    if result != "/":
        assert not result.endswith("/")
```

### Phase 4: Run All Tests (Example + Property)

```bash
pytest tests/test_normalizer.py tests/test_normalizer_properties.py -v

# Hypothesis runs 100 examples per test by default
# Example tests: 2 tests
# Property tests: 3 tests × 100 examples = 300 test cases
# Total: 302 test cases
```

**If property tests find bugs:**
Property tests often generate edge cases you didn't consider:

```python
# Hypothesis found: "\x00//\x00"
# Expected: "\x00/\x00"
# Got: "\x00//\x00" (double slash not removed!)

# Bug revealed: normalize_path doesn't handle null bytes correctly
```

### Phase 5: Fix Bugs and Add Regression Tests

**Fix implementation:**
```python
def normalize_path(path):
    # Handle all character types, not just ASCII
    while "//" in path:  # Loop handles multiple consecutive slashes
        path = path.replace("//", "/")
    if path.endswith("/") and path != "/":
        path = path[:-1]
    return path
```

**Add regression example test:**
```python
def test_normalize_handles_null_bytes():
    """Regression: property test found this edge case"""
    assert normalize_path("\x00//\x00") == "\x00/\x00"
```

**Re-run tests:**
```bash
pytest tests/ -v
# All tests (example + property + regression) should pass
```

## Property Test Patterns

### Idempotence

**Property:** Applying function twice produces same result as applying once

```python
@given(st.text())
def test_function_is_idempotent(input_data):
    result = function(input_data)
    assert function(result) == result
```

**Use for:** Normalization, formatting, sanitization

### Round-Trip

**Property:** Encoding then decoding returns original value

```python
@given(st.dictionaries(st.text(), st.integers()))
def test_json_roundtrip(data):
    """JSON encode/decode preserves data"""
    assert json.loads(json.dumps(data)) == data
```

**Use for:** Serialization, codecs, parsers

### Invariant

**Property:** Certain conditions always hold after operation

```python
@given(st.lists(st.integers()))
def test_filter_size_invariant(items):
    """Filtered list never exceeds original size"""
    filtered = filter_positive(items)
    assert len(filtered) <= len(items)
```

**Use for:** Filtering, transformations, algorithms

### Commutativity

**Property:** Order of operations doesn't matter

```python
@given(st.integers(), st.integers())
def test_add_is_commutative(a, b):
    assert add(a, b) == add(b, a)
```

**Use for:** Mathematical operations, aggregations

### Associativity

**Property:** Grouping doesn't matter

```python
@given(st.integers(), st.integers(), st.integers())
def test_add_is_associative(a, b, c):
    assert add(add(a, b), c) == add(a, add(b, c))
```

**Use for:** Batch operations, recursive algorithms

## Hypothesis Strategies

Common strategies for generating test data:

```python
import hypothesis.strategies as st

# Basic types
st.integers()                    # Any integer
st.integers(min_value=0)         # Non-negative integers
st.floats()                      # Any float
st.text()                        # Any unicode string
st.text(min_size=1)              # Non-empty strings
st.binary()                      # Byte strings
st.booleans()                    # True or False

# Collections
st.lists(st.integers())          # Lists of integers
st.lists(st.text(), min_size=1)  # Non-empty lists of strings
st.dictionaries(st.text(), st.integers())  # String keys, int values
st.tuples(st.integers(), st.text())        # Tuple of (int, str)

# Constrained generation
st.text(alphabet="abc", min_size=5, max_size=10)  # 5-10 chars from "abc"
st.integers(min_value=1, max_value=100)           # Range [1, 100]

# Combining strategies
st.one_of(st.integers(), st.text())  # Either int or str
st.sampled_from([1, 2, 3])           # Pick from list

# Custom strategies
@st.composite
def email_addresses(draw):
    username = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1))
    domain = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1))
    return f"{username}@{domain}.com"
```

## Hypothesis Configuration

### In Test Files

```python
from hypothesis import given, settings, HealthCheck

# Adjust number of examples (default: 100)
@given(st.text())
@settings(max_examples=1000)
def test_with_more_examples(data):
    assert function(data) is not None

# Deadline for each example (default: 200ms)
@given(st.lists(st.integers()))
@settings(deadline=500)  # Allow 500ms per example
def test_slow_function(items):
    assert slow_sort(items) == sorted(items)

# Suppress specific health checks
@given(st.text())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_expensive_operation(data):
    assert validate(data) in [True, False]
```

### In pytest.ini

```ini
[pytest]
# hypothesis settings
hypothesis_profile = default

[hypothesis]
max_examples = 100
deadline = 200
verbosity = normal
```

## Property Test Anti-Patterns

### ❌ Don't

**1. Test UI/stateful code with properties**
```python
# BAD: UI interactions are too stateful for property tests
@given(st.text())
def test_button_click_ui(text):
    button = Button(text)
    button.click()
    assert button.state == "clicked"  # Too much state, too many assumptions
```

**2. Property test external APIs**
```python
# BAD: Real network calls in property tests
@given(st.text())
def test_api_call(query):
    response = requests.get(f"https://api.example.com/search?q={query}")
    assert response.status_code in [200, 404]  # Slow, unreliable, costs money
```

**3. Over-constrain strategies**
```python
# BAD: Too many constraints defeat purpose of property testing
@given(st.text(min_size=5, max_size=5, alphabet="abc"))
def test_function(data):
    # Only 3^5 = 243 possible inputs - just use example tests
    assert function(data) is not None
```

**4. Use property tests as only tests**
```python
# BAD: No example tests showing expected behavior
@given(st.integers())
def test_add(a):
    result = add(a, 0)
    assert result == a  # What does add() do? Not clear from property alone
```

**5. Ignore shrinking failures**
```python
# BAD: Hypothesis found minimal failing case, don't ignore it
@given(st.lists(st.integers()))
def test_sort(items):
    # Hypothesis shrinks [1,2,3,4,5,1000 random items...] → [1,0]
    # Minimal failing case shows real bug!
    try:
        assert custom_sort(items) == sorted(items)
    except AssertionError:
        pass  # BAD: Ignoring the bug hypothesis found
```

### ✅ Do

**1. Start with 1-2 example tests, then add property tests**
```python
# Example test (specific case)
def test_add_positive_numbers():
    assert add(2, 3) == 5

# Property test (general invariant)
@given(st.integers(), st.integers())
def test_add_commutative(a, b):
    assert add(a, b) == add(b, a)
```

**2. Let Hypothesis discover edge cases**
```python
@given(st.text())
def test_parse_username(username):
    result = parse_username(username)
    # Hypothesis will try:
    # - Empty strings: ""
    # - Unicode: "用户"
    # - Special chars: "@#$%"
    # - Very long strings
    # - Null bytes, newlines, etc.
    assert isinstance(result, (str, type(None)))
```

**3. Add regression example tests when property tests find bugs**
```python
# Hypothesis found: normalize_path("///") → "//" (bug!)
# Add regression test:
def test_normalize_multiple_slashes_at_root():
    """Regression: hypothesis found triple slash edge case"""
    assert normalize_path("///") == "/"
```

**4. Use `hypothesis.assume()` for input constraints**
```python
from hypothesis import given, assume

@given(st.integers(), st.integers())
def test_divide(a, b):
    assume(b != 0)  # Constrain input space
    result = divide(a, b)
    assert result * b == a  # Property: division inverse of multiplication
```

**5. Run property tests in CI with reasonable `max_examples`**
```python
# In CI: balance coverage vs. speed
@given(st.text())
@settings(max_examples=100)  # Fast enough for CI
def test_function_in_ci(data):
    assert function(data) is not None
```

## TDD Guard Integration

Property tests are treated like any other tests:

**1. Generate test.json**
```bash
pytest tests/ -v
# Includes both example and property tests
```

**2. TDD Guard validation**
```bash
# PreToolUse hook validates test.json
# If property tests cover code, Write/Edit allowed
```

**3. Coverage metrics**
```bash
pytest tests/ --cov --cov-report=term-missing
# Shows coverage from example + property tests combined
```

## Hypothesis Debugging

### Reproduce Failures

Hypothesis prints minimal failing example:

```
Falsifying example: test_function(
    input_data='x\x00'
)
```

Copy this into a regression test:

```python
def test_regression_null_byte():
    """Regression: hypothesis found null byte edge case"""
    assert function('x\x00') == expected_value
```

### Understand Shrinking

Hypothesis automatically simplifies failing examples:

```
Original failure: [1, 2, 3, 4, 5, ..., 1000 elements]
Shrunk to:        [0, 1]  # Minimal case that still fails
```

The shrunk example reveals the core bug without noise.

### Verbosity

Increase verbosity to see what Hypothesis is testing:

```python
@given(st.text())
@settings(verbosity=hypothesis.Verbosity.verbose)
def test_with_logging(data):
    assert function(data) is not None
```

Output shows each generated example.

## Performance Considerations

**Property tests are slower than example tests:**
- 100 examples per property test (default)
- Each example runs full test logic
- Total: `num_property_tests × max_examples` test cases

**Optimization strategies:**
1. Reduce `max_examples` in CI (e.g., 50 instead of 100)
2. Use `@settings(deadline=None)` for expensive operations
3. Run property tests in separate CI job (parallel with other tests)
4. Use `pytest -m "not property"` to skip property tests during development

**Example pytest.ini configuration:**
```ini
[pytest]
markers =
    property: Property-based tests (run in CI only)
    slow: Slow tests (run nightly)
```

Mark property tests:
```python
import pytest

@pytest.mark.property
@given(st.text())
def test_property(data):
    assert function(data) is not None
```

Run without property tests:
```bash
pytest -m "not property"  # Fast local development
pytest                     # Full suite in CI
```

## Example: Complete TDD Workflow

```python
# Step 1: Example test (RED)
def test_deduplicate_removes_consecutive_duplicates():
    assert deduplicate([1, 1, 2, 3, 3]) == [1, 2, 3]

# Step 2: Minimal implementation (GREEN)
def deduplicate(items):
    result = []
    prev = object()  # Sentinel
    for item in items:
        if item != prev:
            result.append(item)
            prev = item
    return result

# Step 3: Property tests (REFACTOR)
from hypothesis import given
import hypothesis.strategies as st

@given(st.lists(st.integers()))
def test_deduplicate_length_invariant(items):
    """Result never longer than input"""
    assert len(deduplicate(items)) <= len(items)

@given(st.lists(st.integers()))
def test_deduplicate_preserves_order(items):
    """Relative order preserved"""
    result = deduplicate(items)
    # All items in result should appear in same order in original
    original_iter = iter(items)
    for item in result:
        while next(original_iter) != item:
            pass  # Scan forward in original until found

@given(st.lists(st.integers()))
def test_deduplicate_no_consecutive_duplicates(items):
    """Output has no consecutive duplicates"""
    result = deduplicate(items)
    for i in range(len(result) - 1):
        assert result[i] != result[i + 1]

# Run all tests
# pytest tests/test_deduplicate.py -v
# 1 example test + 3 property tests × 100 examples = 301 test cases
```

## See Also

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Property-Based Testing Guide](https://increment.com/testing/in-praise-of-property-based-testing/)
- `/property-test` command documentation (CLAUDE.md)
- TDD Guard property testing integration (CLAUDE.md lines 734-812)
