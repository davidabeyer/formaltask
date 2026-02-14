# Hypothesis Property Patterns

Common property patterns with implementation examples for strategizing-tests skill.

## Roundtrip Properties

Test that transformations can be reversed without data loss.

### Encode/Decode

```python
from hypothesis import given, strategies as st

@given(st.binary())
def test_base64_roundtrip(data: bytes):
    """Base64 encode/decode preserves original data."""
    encoded = base64.b64encode(data)
    decoded = base64.b64decode(encoded)
    assert decoded == data

@given(st.text())
def test_json_roundtrip(text: str):
    """JSON serialization preserves string data."""
    # Note: JSON can't handle all unicode, filter appropriately
    encoded = json.dumps(text)
    decoded = json.loads(encoded)
    assert decoded == text
```

### Parse/Format

```python
from hypothesis import given, strategies as st, assume
from datetime import datetime

@given(st.datetimes())
def test_datetime_iso_roundtrip(dt: datetime):
    """ISO format parsing is reversible."""
    formatted = dt.isoformat()
    parsed = datetime.fromisoformat(formatted)
    assert parsed == dt

@given(st.from_regex(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', fullmatch=True))
def test_ip_address_roundtrip(ip_str: str):
    """IP address parsing preserves value."""
    # Filter valid IPs only
    parts = [int(p) for p in ip_str.split('.')]
    assume(all(0 <= p <= 255 for p in parts))

    parsed = parse_ip(ip_str)
    formatted = format_ip(parsed)
    assert formatted == ip_str
```

### Compress/Decompress

```python
import gzip

@given(st.binary(max_size=10000))  # Limit size for performance
def test_gzip_roundtrip(data: bytes):
    """Compression is lossless."""
    compressed = gzip.compress(data)
    decompressed = gzip.decompress(compressed)
    assert decompressed == data
```

## Invariant Properties

Test that certain properties always hold.

### Length Invariants

```python
@given(st.lists(st.integers()))
def test_filter_never_increases_length(items: list):
    """Filtering can only remove or preserve elements."""
    result = filter_positive(items)
    assert len(result) <= len(items)

@given(st.lists(st.integers()))
def test_sort_preserves_length(items: list):
    """Sorting doesn't add or remove elements."""
    result = sorted(items)
    assert len(result) == len(items)

@given(st.lists(st.integers()))
def test_dedupe_never_increases_length(items: list):
    """Deduplication removes or preserves elements."""
    result = dedupe(items)
    assert len(result) <= len(items)
```

### Content Invariants

```python
@given(st.lists(st.integers()))
def test_sort_preserves_elements(items: list):
    """Sorting doesn't change which elements exist."""
    result = sorted(items)
    assert sorted(result) == sorted(items)  # Same multiset

@given(st.lists(st.integers(), min_size=1))
def test_shuffle_preserves_elements(items: list):
    """Shuffling preserves all elements."""
    result = shuffle(items.copy())
    assert sorted(result) == sorted(items)

@given(st.lists(st.text()))
def test_transform_preserves_count(items: list):
    """Mapping preserves element count."""
    result = [transform(x) for x in items]
    assert len(result) == len(items)
```

### Ordering Invariants

```python
@given(st.lists(st.integers()))
def test_sort_produces_ordered_output(items: list):
    """Sorted output is always in order."""
    result = sorted(items)
    for i in range(len(result) - 1):
        assert result[i] <= result[i + 1]

@given(st.lists(st.integers(), min_size=1))
def test_max_is_greatest(items: list):
    """Max returns the largest element."""
    result = max(items)
    assert all(x <= result for x in items)
```

## Idempotence Properties

Test that applying operation twice equals applying once.

```python
@given(st.text())
def test_normalize_is_idempotent(text: str):
    """Normalizing twice equals normalizing once."""
    once = normalize(text)
    twice = normalize(once)
    assert twice == once

@given(st.lists(st.integers()))
def test_dedupe_is_idempotent(items: list):
    """Deduplicating twice equals deduplicating once."""
    once = dedupe(items)
    twice = dedupe(once)
    assert twice == once

@given(st.text())
def test_strip_is_idempotent(text: str):
    """Stripping whitespace twice equals once."""
    once = text.strip()
    twice = once.strip()
    assert twice == once
```

## Commutativity Properties

Test that order of operations doesn't matter.

```python
@given(st.integers(), st.integers())
def test_addition_is_commutative(a: int, b: int):
    """a + b == b + a"""
    assert add(a, b) == add(b, a)

@given(st.sets(st.integers()), st.sets(st.integers()))
def test_union_is_commutative(a: set, b: set):
    """Set union is commutative."""
    assert a | b == b | a

@given(st.sets(st.integers()), st.sets(st.integers()))
def test_intersection_is_commutative(a: set, b: set):
    """Set intersection is commutative."""
    assert a & b == b & a
```

## Metamorphic Properties

Test relationships between inputs and outputs.

```python
@given(st.lists(st.integers()))
def test_reverse_twice_is_identity(items: list):
    """Reversing twice returns original."""
    result = list(reversed(list(reversed(items))))
    assert result == items

@given(st.lists(st.integers()), st.integers())
def test_append_increases_length_by_one(items: list, element: int):
    """Appending always adds exactly one element."""
    original_len = len(items)
    items.append(element)
    assert len(items) == original_len + 1

@given(st.text())
def test_upper_length_equals_original(text: str):
    """Uppercasing preserves string length."""
    assert len(text.upper()) == len(text)
```

## Domain-Specific Patterns

### Database Records

```python
@st.composite
def user_strategy(draw):
    """Generate valid user records."""
    return {
        'id': draw(st.uuids()),
        'email': draw(st.emails()),
        'name': draw(st.text(min_size=1, max_size=100)),
        'created_at': draw(st.datetimes()),
    }

@given(user_strategy())
def test_user_serialization_roundtrip(user: dict):
    """User can be serialized and deserialized."""
    serialized = serialize_user(user)
    deserialized = deserialize_user(serialized)
    assert deserialized == user
```

### API Responses

```python
@st.composite
def api_response_strategy(draw):
    """Generate valid API response structures."""
    return {
        'status': draw(st.sampled_from(['success', 'error'])),
        'data': draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.text() | st.integers() | st.booleans()
        )),
        'timestamp': draw(st.datetimes()).isoformat(),
    }

@given(api_response_strategy())
def test_response_validation_accepts_valid(response: dict):
    """Validator accepts all valid responses."""
    assert validate_response(response) is True
```

### File Paths

```python
from hypothesis import given, strategies as st

# Path components without problematic characters
path_component = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),  # Letters and numbers
        whitelist_characters='-_.'
    ),
    min_size=1,
    max_size=50
)

@given(st.lists(path_component, min_size=1, max_size=10))
def test_path_join_split_roundtrip(parts: list):
    """Joining then splitting preserves path parts."""
    joined = '/'.join(parts)
    split = joined.split('/')
    assert split == parts
```

## Anti-Patterns to Avoid

### Too Broad Strategies

```python
# BAD: Too permissive, generates invalid inputs
@given(st.text())
def test_email_validation(email: str):
    # Will generate "abc" which isn't a valid email format
    pass

# GOOD: Constrained to valid domain
@given(st.emails())
def test_email_validation(email: str):
    # Generates only valid email formats
    pass
```

### Missing Assumptions

```python
# BAD: Division by zero possible
@given(st.integers(), st.integers())
def test_division(a: int, b: int):
    result = a / b  # ZeroDivisionError when b=0

# GOOD: Assume valid inputs
@given(st.integers(), st.integers())
def test_division(a: int, b: int):
    assume(b != 0)
    result = a / b
    assert result * b == a  # With floating point tolerance
```

### Overly Complex Properties

```python
# BAD: Testing implementation details
@given(st.lists(st.integers()))
def test_sort_uses_quicksort(items: list):
    # Property testing should test behavior, not algorithms
    pass

# GOOD: Test observable behavior
@given(st.lists(st.integers()))
def test_sort_produces_ordered_output(items: list):
    result = sorted(items)
    assert all(result[i] <= result[i+1] for i in range(len(result)-1))
```

## Performance Considerations

### Size Limits

```python
# Limit input sizes for performance
@given(st.lists(st.integers(), max_size=1000))
def test_large_list_operation(items: list):
    pass

# Use settings for slow tests
from hypothesis import settings

@settings(max_examples=50)  # Fewer examples for slow tests
@given(st.binary(max_size=100000))
def test_compression(data: bytes):
    pass
```

### Deadline Settings

```python
from hypothesis import settings, Verbosity

@settings(
    deadline=1000,  # 1 second max per example
    suppress_health_check=[HealthCheck.too_slow]
)
@given(complex_strategy())
def test_slow_operation(data):
    pass
```
