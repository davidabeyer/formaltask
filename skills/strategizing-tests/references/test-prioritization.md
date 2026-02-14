# Test Prioritization Framework

Guide for determining which tests to write first and how to order execution.

## Risk-Based Prioritization

### P0: Critical Path Tests

Tests that must exist before any deployment:

**Criteria:**
- Data integrity (can lose or corrupt user data)
- Security (authentication, authorization, input validation)
- Financial transactions (payments, billing, credits)
- Core business logic (primary value proposition)

**Examples:**
```python
# P0: Security - authentication
def test_login_with_invalid_password_fails(): ...
def test_session_expires_after_timeout(): ...

# P0: Data integrity
def test_database_transaction_rolls_back_on_error(): ...
def test_backup_restores_correctly(): ...

# P0: Financial
def test_payment_amount_matches_order_total(): ...
def test_refund_cannot_exceed_original_payment(): ...
```

**Property Tests for P0:**
```python
# Data integrity properties
@given(user_data_strategy())
def test_user_data_survives_serialization_roundtrip(data):
    """User data is never corrupted during save/load."""
    saved = serialize(data)
    loaded = deserialize(saved)
    assert loaded == data

# Security properties
@given(st.text())
def test_sanitizer_removes_all_script_tags(input_text):
    """XSS prevention is complete."""
    result = sanitize(input_text)
    assert '<script' not in result.lower()
```

### P1: Core Functionality Tests

Tests for primary features that users interact with daily:

**Criteria:**
- Main user workflows (create, read, update, delete)
- API endpoints used by frontend
- Data processing pipelines
- Integration with critical third parties

**Examples:**
```python
# P1: Core workflow
def test_user_can_create_project(): ...
def test_user_can_invite_team_member(): ...

# P1: API endpoints
def test_list_projects_returns_paginated_results(): ...
def test_search_filters_by_date_range(): ...
```

### P2: Edge Cases and Error Handling

Tests for uncommon scenarios and error recovery:

**Criteria:**
- Empty inputs, null values
- Boundary conditions (max length, min values)
- Error messages and user feedback
- Retry logic and timeout handling

**Examples:**
```python
# P2: Edge cases
def test_empty_list_returns_empty_result(): ...
def test_max_length_input_is_accepted(): ...

# P2: Error handling
def test_network_timeout_shows_retry_button(): ...
def test_invalid_input_shows_helpful_message(): ...
```

## Dependency Ordering

### Test Execution Dependencies

Some tests must run after others:

```python
# Order: unit → integration → e2e

# 1. Unit tests (no dependencies)
def test_validator_rejects_empty_email(): ...
def test_hasher_produces_consistent_output(): ...

# 2. Integration tests (depend on unit-tested components)
def test_registration_validates_and_hashes_password(): ...

# 3. E2E tests (depend on integration)
def test_user_can_register_and_login(): ...
```

### Component Dependencies

Test dependencies before dependents:

```
Database Layer → Repository → Service → Controller → API
     ↓              ↓           ↓          ↓          ↓
   First        Second       Third     Fourth      Last
```

**Practical ordering:**
```python
# Phase 1: Foundation
test_db_connection_succeeds()
test_db_migration_applies_cleanly()

# Phase 2: Data layer
test_user_repository_creates_record()
test_user_repository_finds_by_id()

# Phase 3: Business logic
test_user_service_validates_email()
test_user_service_hashes_password()

# Phase 4: API layer
test_registration_endpoint_creates_user()
test_login_endpoint_returns_token()
```

## Coverage Optimization

### Maximum Coverage, Minimum Tests

**Strategy: Test boundaries and representatives**

```python
# Instead of testing every integer:
def test_positive_number(): assert validate(1)
def test_negative_number(): assert validate(-1)
def test_zero(): assert validate(0)
def test_max_int(): assert validate(sys.maxsize)
def test_min_int(): assert validate(-sys.maxsize)

# Instead of testing every string:
def test_empty_string(): ...
def test_single_char(): ...
def test_unicode_string(): ...
def test_max_length_string(): ...
```

**Use Hypothesis for boundary exploration:**
```python
@given(st.integers())
def test_integer_validation(n: int):
    """Hypothesis finds edge cases automatically."""
    result = validate(n)
    assert isinstance(result, bool)
```

### Coverage Metrics Targets

| Test Type | Line Coverage | Branch Coverage | Property Count |
|-----------|---------------|-----------------|----------------|
| P0 Critical | 100% | 100% | 2-3 per component |
| P1 Core | 90% | 85% | 1-2 per component |
| P2 Edge | 80% | 75% | As needed |

## Test Writing Order

### Phase 1: Property Tests (Foundation)

Write property tests first for:
1. Data transformations (encode/decode, parse/format)
2. Validators (input validation, business rules)
3. Pure functions (no side effects)

**Why first:**
- Property tests find edge cases you wouldn't think of
- They document invariants explicitly
- They provide confidence before implementation

```python
# Write these BEFORE unit tests
@given(st.binary())
def test_codec_roundtrip(data): ...

@given(email_strategy())
def test_email_validation_accepts_valid(email): ...
```

### Phase 2: Unit Tests (Behavior)

Write unit tests for:
1. Error handling paths
2. Specific business scenarios
3. State transitions
4. Configuration handling

**After properties because:**
- Properties cover happy paths broadly
- Units cover specific scenarios properties might miss
- Units document expected behavior explicitly

```python
# Specific scenarios
def test_login_with_locked_account_shows_unlock_option(): ...
def test_password_reset_expires_after_24_hours(): ...
```

### Phase 3: Integration Tests (Flows)

Write integration tests for:
1. Critical user journeys
2. Cross-component interactions
3. External service integrations

**Last because:**
- Depend on unit-tested components
- Slower to run
- More brittle (more moving parts)

```python
# Full flow tests
def test_user_registration_to_first_project_creation(): ...
def test_payment_flow_with_stripe_webhook(): ...
```

## Test Estimation

### Estimating Test Count

| Component Complexity | Unit Tests | Property Tests | Integration |
|---------------------|------------|----------------|-------------|
| Simple (1 file, no deps) | 3-5 | 1-2 | 0 |
| Medium (2-3 files, 1 dep) | 5-10 | 2-3 | 1-2 |
| Complex (3+ files, multi deps) | 10-20 | 3-5 | 3-5 |

### Time Estimation (After Initial Setup)

| Test Type | Time per Test | Notes |
|-----------|--------------|-------|
| Property test | 15-30 min | Strategy design is the hard part |
| Unit test | 5-15 min | Straightforward if component is testable |
| Integration test | 30-60 min | Setup and teardown complexity |

## Continuous Prioritization

### During Development

```
New feature request
        ↓
Identify P0 tests → Write immediately
        ↓
Identify P1 tests → Write before PR
        ↓
Identify P2 tests → Write before release
```

### During Bug Fixes

```
Bug reported
     ↓
Write failing test (P0 if critical, P1 otherwise)
     ↓
Fix bug
     ↓
Verify test passes
     ↓
Consider: Is this a property? Add Hypothesis test.
```

### Refactoring

```
Plan refactoring
       ↓
Ensure P0/P1 tests exist for affected code
       ↓
Run tests continuously during refactor
       ↓
Add P2 tests for edge cases discovered
```

## Quick Reference

### Test Priority Decision Tree

```
Is failure a security issue? → P0
Is failure data loss/corruption? → P0
Is failure financial impact? → P0
Is failure breaking core workflow? → P1
Is failure edge case/rare scenario? → P2
```

### What to Test First for New Component

1. **Property test** for main transformation/validation
2. **Unit test** for error handling
3. **Integration test** for primary use case

### What to Skip (Initially)

- Trivial getters/setters
- Framework-provided functionality
- UI layout (test logic, not appearance)
- Third-party library internals
