# Waste Patterns

Detailed examples of code waste and how to eliminate it.

---

## 1. Abstraction Addiction

**Symptom**: Interface → AbstractBase → ConcreteBase → Implementation

```python
# WASTE: 4 layers for one thing
class IUserRepository(ABC):
    @abstractmethod
    def find(self, id): ...

class BaseUserRepository(IUserRepository):
    def __init__(self, db): self.db = db

class SQLUserRepository(BaseUserRepository):
    def find(self, id):
        return self.db.query(User).get(id)

# Using it requires:
repo = SQLUserRepository(db)
user = repo.find(id)

# SIMPLE: Just a function
def find_user(db, id):
    return db.query(User).get(id)

user = find_user(db, id)
```

**Rule**: Only create interface if you have 2+ implementations TODAY.

---

## 2. Factory Factory

**Symptom**: Creating factories to create builders to create objects

```python
# WASTE
class UserFactory:
    def create_builder(self):
        return UserBuilder()

class UserBuilder:
    def __init__(self):
        self.user = User()
    def with_name(self, name):
        self.user.name = name
        return self
    def build(self):
        return self.user

user = UserFactory().create_builder().with_name("Bob").build()

# SIMPLE
user = User(name="Bob")
```

**Rule**: Direct instantiation unless construction is genuinely complex.

---

## 3. Utils Graveyard

**Symptom**: utils.py with 50 unrelated functions

```python
# WASTE: utils.py
def format_date(d): ...
def validate_email(e): ...
def calculate_tax(amount): ...
def send_notification(msg): ...
def parse_config(path): ...
# ... 45 more unrelated functions

# SIMPLE: Inline single-use, co-locate related
# If format_date is only used in reports.py, put it in reports.py
# If validate_email is used everywhere, that's fine - but just that one function
```

**Rule**: Inline if used once. Co-locate with caller if used 2-3 times in same module.

---

## 4. Config Madness

**Symptom**: 20 options, 2 ever used

```python
# WASTE
config = {
    "max_retries": 3,
    "timeout": 30,
    "backoff_multiplier": 2,
    "backoff_max": 300,
    "jitter": True,
    "jitter_range": 0.1,
    "circuit_breaker_threshold": 5,
    "circuit_breaker_timeout": 60,
    # ... 12 more options nobody changes
}

# SIMPLE: Hardcode defaults, expose only what varies
MAX_RETRIES = 3
TIMEOUT = 30

def fetch_with_retry(url):
    for i in range(MAX_RETRIES):
        try:
            return requests.get(url, timeout=TIMEOUT)
        except Timeout:
            time.sleep(2 ** i)
```

**Rule**: Config is for things that ACTUALLY vary between environments.

---

## 5. Type Gymnastics

**Symptom**: `Generic<T extends Foo<Bar<Baz>>>`

```python
# WASTE
T = TypeVar('T', bound='Serializable')
U = TypeVar('U', bound='Validatable')

class DataProcessor(Generic[T, U]):
    def __init__(self, serializer: Serializer[T], validator: Validator[U]):
        self.serializer = serializer
        self.validator = validator

    def process(self, data: T) -> U:
        validated = self.validator.validate(data)
        return self.serializer.serialize(validated)

# Used exactly once with User and UserDTO

# SIMPLE
def process_user(user: User) -> UserDTO:
    validate_user(user)
    return serialize_user(user)
```

**Rule**: Use generics only when you have 3+ concrete uses TODAY.

---

## 6. Middleware Stack

**Symptom**: Request passes through 8 layers

```python
# WASTE: 8 middleware layers
app.use(logging_middleware)
app.use(auth_middleware)
app.use(rate_limit_middleware)
app.use(cors_middleware)
app.use(compression_middleware)
app.use(cache_middleware)
app.use(validation_middleware)
app.use(error_middleware)

# Each adds overhead, debugging is nightmare

# SIMPLE: Combine related, inline trivial
@app.before_request
def before():
    log_request()
    check_auth()
    check_rate_limit()

@app.after_request
def after(response):
    add_cors_headers(response)
    return response
```

**Rule**: Middleware for cross-cutting concerns only. Inline the rest.

---

## 7. DTO Explosion

**Symptom**: 10 classes to pass data between 2 functions

```python
# WASTE
class UserCreateRequest: ...
class UserCreateDTO: ...
class UserEntity: ...
class UserResponse: ...
class UserSummaryDTO: ...

def create_user(request: UserCreateRequest) -> UserResponse:
    dto = UserCreateDTO.from_request(request)
    entity = UserEntity.from_dto(dto)
    saved = repo.save(entity)
    return UserResponse.from_entity(saved)

# SIMPLE
def create_user(name: str, email: str) -> dict:
    user = {"name": name, "email": email, "id": generate_id()}
    db.users.insert(user)
    return user
```

**Rule**: Use dict for internal data passing. Classes only at API boundaries.

---

## 8. Premature Generalization

**Symptom**: Generic solution for one use case

```python
# WASTE: Plugin system with one plugin
class PluginManager:
    def __init__(self):
        self.plugins = {}
    def register(self, name, plugin):
        self.plugins[name] = plugin
    def execute(self, name, *args):
        return self.plugins[name].run(*args)

manager = PluginManager()
manager.register("email", EmailPlugin())
# Only ever used with email

# SIMPLE
def send_email(to, subject, body):
    # Just send the email
    ...
```

**Rule**: Build plugin systems when you have 3+ plugins. Not before.

---

## Detection Checklist

Before simplifying, verify:

- [ ] Grepped all usages of target code
- [ ] Identified all callers
- [ ] Found all tests
- [ ] Confirmed pattern is actually waste (not intentional design)

After simplifying, verify:

- [ ] All tests pass
- [ ] No functionality changed
- [ ] Net lines decreased
- [ ] Readability improved
