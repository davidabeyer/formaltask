# The Five Testing Anti-Patterns

## Anti-Pattern 1: Testing Mock Behavior Instead of Real Behavior

**The Problem:**
Tests verify that mocks work correctly rather than testing actual component behavior.

**JavaScript/TypeScript Example (BAD):**
```typescript
// Testing that mock exists, not that component works
test('renders user profile', () => {
  const mockUser = { name: 'Alice' };
  render(<UserProfile user={mockUser} />);

  // This only verifies the mock has 'Alice', not that component displays it
  const element = screen.getByTestId('user-name');
  expect(element).toHaveTextContent('Alice'); // Testing mock data, not component
});
```

**Why it's wrong:** If the component never actually renders the name, this test still passes because it's verifying mock data was passed correctly, not that the UI works.

**Python Example (BAD):**
```python
# Testing mock behavior instead of function logic
def test_process_user_data(mocker):
    mock_validator = mocker.Mock(return_value=True)

    # This only tests the mock was called, not that validation actually works
    result = process_user({'name': 'Alice'}, validator=mock_validator)

    mock_validator.assert_called_once()  # Verifying mock, not behavior
    assert result is not None  # Weak assertion
```

**Good (Test Real Behavior):**
```python
def test_process_user_data_validates_email():
    """Test actual validation behavior, not mocks."""
    # Use real validator or test double that implements validation logic
    validator = EmailValidator()  # Real object

    # Test actual behavior with invalid data
    with pytest.raises(ValidationError, match="Invalid email"):
        process_user({'name': 'Alice', 'email': 'invalid'}, validator=validator)

    # Test actual behavior with valid data
    result = process_user({'name': 'Alice', 'email': 'alice@example.com'}, validator=validator)
    assert result['email'] == 'alice@example.com'
    assert result['name'] == 'Alice'
```

**TypeScript Example (GOOD):**
```typescript
// Test actual component behavior
test('displays user name in UI', () => {
  render(<UserProfile user={{ name: 'Alice', email: 'alice@example.com' }} />);

  // Verify actual DOM output, not mock data
  const heading = screen.getByRole('heading', { name: /alice/i });
  expect(heading).toBeInTheDocument();

  // Verify component handles missing data correctly
  rerender(<UserProfile user={{ name: '', email: 'test@example.com' }} />);
  expect(screen.getByText(/anonymous/i)).toBeInTheDocument();
});
```

**When to Mock vs Use Real Objects:**
- Mock: External APIs, databases, file systems, network calls
- Real: Business logic, validators, transformers, formatters
- Real: Internal dependencies you control

---

## Anti-Pattern 2: Test-Only Methods in Production Code

**The Problem:**
Adding methods to production classes solely for test teardown or setup pollutes the API.

**Python Example (BAD):**
```python
# Production class polluted with test-only method
class DatabaseConnection:
    def __init__(self, host: str):
        self.host = host
        self._connection = None

    def connect(self):
        self._connection = create_connection(self.host)

    def query(self, sql: str):
        return self._connection.execute(sql)

    def destroy(self):  # Only exists for tests
        """Clean up connection for tests."""
        if self._connection:
            self._connection.close()
            self._connection = None

# Test using test-only method
def test_query_returns_results():
    db = DatabaseConnection('localhost')
    db.connect()
    results = db.query("SELECT * FROM users")
    assert len(results) > 0
    db.destroy()  # Using test-only method
```

**Why it's wrong:**
- Production code gains methods never used in production
- API surface increases unnecessarily
- Violates single responsibility principle
- Confuses future developers ("When should I call destroy()?")

**Good (Test Utility Functions):**
```python
# Production class has only production methods
class DatabaseConnection:
    def __init__(self, host: str):
        self.host = host
        self._connection = None

    def connect(self):
        self._connection = create_connection(self.host)

    def query(self, sql: str):
        return self._connection.execute(sql)

    def close(self):  # Legitimate production method
        if self._connection:
            self._connection.close()

# Test utility function (in conftest.py or test_helpers.py)
@pytest.fixture
def database_connection():
    """Fixture handles setup/teardown without polluting production code."""
    db = DatabaseConnection('localhost')
    db.connect()
    yield db
    db.close()  # Uses legitimate production method

# Test uses fixture
def test_query_returns_results(database_connection):
    results = database_connection.query("SELECT * FROM users")
    assert len(results) > 0
    # Cleanup happens automatically via fixture
```

**TypeScript Example (BAD):**
```typescript
// Test-only method pollutes interface
class UserService {
  private users: Map<string, User> = new Map();

  async createUser(user: User): Promise<void> {
    this.users.set(user.id, user);
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  // Only for tests
  clearAllUsers(): void {
    this.users.clear();
  }
}
```

**Good (Test Helper):**
```typescript
// Production class clean
class UserService {
  private users: Map<string, User> = new Map();

  async createUser(user: User): Promise<void> {
    this.users.set(user.id, user);
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }
}

// Test helper function
function createFreshUserService(): UserService {
  return new UserService(); // Fresh instance = clean state
}

// Test uses helper
test('creates and retrieves user', async () => {
  const service = createFreshUserService();
  await service.createUser({ id: '1', name: 'Alice' });
  const user = await service.getUser('1');
  expect(user?.name).toBe('Alice');
});
```

**Legitimate exceptions:**
- Dependency injection setters (production use case)
- Debug/diagnostic methods (production troubleshooting)
- Lifecycle methods required by framework (e.g., Django's `save()`, `delete()`)

---

## Anti-Pattern 3: Blind Mocking (Mocking Without Understanding)

**The Problem:**
Mocking methods without understanding what they do or why they're needed.

**Python Example (BAD):**
```python
# Blindly mocking without understanding side effects
def test_send_notification(mocker):
    mock_logger = mocker.patch('app.logger')
    mock_email = mocker.patch('app.email_service.send')
    mock_db = mocker.patch('app.db.save_notification')

    # What do these do? Why are we mocking them all?
    send_notification(user_id='123', message='Hello')

    # Verifying mocks were called doesn't test behavior
    mock_logger.info.assert_called()
    mock_email.assert_called()
    mock_db.assert_called()
```

**Why it's wrong:**
- Don't know what `logger.info()` does - might have side effects we need to test
- Don't know if `db.save_notification()` should happen before or after email
- Can't verify notification was actually sent correctly
- Test passes even if function is completely broken

**Good (Mock Selectively with Understanding):**
```python
# Mock only external dependencies, test actual logic
def test_send_notification_creates_record_and_sends_email(mocker):
    """Test notification flow: DB record -> email send -> logging."""

    # Mock ONLY the email service (external dependency)
    mock_send_email = mocker.patch('app.email_service.send', return_value={'id': 'email-123'})

    # Use real database (in-memory SQLite for tests)
    test_db = create_test_database()

    # Test actual behavior
    result = send_notification(
        user_id='123',
        message='Hello',
        db=test_db
    )

    # Verify database record created (real behavior)
    notification = test_db.get_notification(result['notification_id'])
    assert notification.user_id == '123'
    assert notification.message == 'Hello'
    assert notification.status == 'sent'

    # Verify email sent with correct data (mocked external call)
    mock_send_email.assert_called_once_with(
        to='user-123@example.com',
        subject='Notification',
        body='Hello'
    )
```

**Decision tree for mocking:**
```
Is this an external dependency? (API, file system, network)
|-- YES -> Mock it
|-- NO  -> Is this slow? (>100ms)
    |-- YES -> Consider test double or in-memory alternative
    |-- NO  -> Use the real implementation
```

---

## Anti-Pattern 4: Incomplete Mocks

**The Problem:**
Mock responses contain only the minimum fields needed to pass the current test, breaking when downstream code needs other fields.

**Python Example (BAD):**
```python
# Incomplete mock - only includes fields used in test
def test_format_user_profile(mocker):
    mock_api = mocker.patch('app.api.get_user')
    mock_api.return_value = {
        'name': 'Alice'  # Real API returns 20+ fields
    }

    profile = format_user_profile(user_id='123')
    assert 'Alice' in profile
    # Passes now, breaks when format_user_profile needs 'email' field
```

**Why it's wrong:**
- Fragile: Adding a field to `format_user_profile` breaks unrelated tests
- False confidence: Test passes but production fails
- Maintenance burden: Every test breaks when API contract changes

**Good (Complete Mocks):**
```python
# Complete mock mirrors actual API response
def create_user_response(overrides: dict = None) -> dict:
    """Factory for complete user API responses."""
    default = {
        'id': '123',
        'name': 'Alice',
        'email': 'alice@example.com',
        'avatar_url': 'https://example.com/avatar.jpg',
        'role': 'user',
        'created_at': '2025-01-01T00:00:00Z',
        'updated_at': '2025-01-01T00:00:00Z',
        'is_active': True,
        'metadata': {},
        # ... all fields from real API
    }
    if overrides:
        default.update(overrides)
    return default

def test_format_user_profile(mocker):
    mock_api = mocker.patch('app.api.get_user')
    mock_api.return_value = create_user_response({'name': 'Alice'})

    profile = format_user_profile(user_id='123')
    assert 'Alice' in profile
    # Won't break when format_user_profile uses other fields
```

**TypeScript Example (GOOD):**
```typescript
// Type-safe complete mock factory
interface User {
  id: string;
  name: string;
  email: string;
  avatarUrl: string;
  role: 'admin' | 'user';
  createdAt: Date;
  isActive: boolean;
}

function createMockUser(overrides?: Partial<User>): User {
  return {
    id: '123',
    name: 'Test User',
    email: 'test@example.com',
    avatarUrl: 'https://example.com/avatar.jpg',
    role: 'user',
    createdAt: new Date('2025-01-01'),
    isActive: true,
    ...overrides
  };
}

// Test uses complete mock with overrides
test('formats admin user profile differently', () => {
  const adminUser = createMockUser({ role: 'admin', name: 'Admin Alice' });
  const profile = formatUserProfile(adminUser);
  expect(profile).toContain('Admin Alice');
});
```

**When to use factories:**
- API response mocks (external services)
- Database record mocks (ORM objects)
- Complex object graphs (nested structures)

---

## Anti-Pattern 5: Deferred Testing

**The Problem:**
Treating tests as optional follow-up work rather than integral to development.

**Manifestations:**
```python
# Implementation without test
def calculate_discount(price: float, tier: str) -> float:
    if tier == 'gold':
        return price * 0.8
    elif tier == 'silver':
        return price * 0.9
    return price
# "I'll write tests after this ships"
```

**Why it's wrong:**
- No verification the code works
- Bugs discovered in production
- Harder to test after implementation
- Encourages design that's hard to test
- Tests never get written (or rushed/inadequate)

**Good (TDD Approach):**
```python
# Test first (RED phase)
def test_calculate_discount_gold_tier_gets_20_percent_off():
    """Gold tier customers get 20% discount."""
    assert calculate_discount(100.0, 'gold') == 80.0

def test_calculate_discount_silver_tier_gets_10_percent_off():
    """Silver tier customers get 10% discount."""
    assert calculate_discount(100.0, 'silver') == 90.0

def test_calculate_discount_standard_tier_gets_no_discount():
    """Standard tier customers pay full price."""
    assert calculate_discount(100.0, 'standard') == 100.0

# Run tests -> FAIL (function doesn't exist yet)

# Implementation (GREEN phase)
def calculate_discount(price: float, tier: str) -> float:
    """Calculate discount based on customer tier."""
    if tier == 'gold':
        return price * 0.8
    elif tier == 'silver':
        return price * 0.9
    return price

# Run tests -> PASS (verified working)

# Refactor (REFACTOR phase)
TIER_DISCOUNTS = {
    'gold': 0.2,
    'silver': 0.1,
    'standard': 0.0
}

def calculate_discount(price: float, tier: str) -> float:
    """Calculate discount based on customer tier."""
    discount_rate = TIER_DISCOUNTS.get(tier, 0.0)
    return price * (1 - discount_rate)

# Run tests -> STILL PASS (refactoring safe)
```

**How TDD prevents deferred testing:**
- Tests written first = impossible to defer
- Red-Green-Refactor cycle enforces discipline
- tdd-guard blocks implementation without tests (technical enforcement)
