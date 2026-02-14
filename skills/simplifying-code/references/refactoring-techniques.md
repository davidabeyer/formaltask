# Refactoring Techniques

Step-by-step techniques for simplifying code safely.

---

## 1. Inline Function

**When**: Function called 1-2 times, body is simple

**Steps**:
1. Find all call sites: `grep -r "function_name(" .`
2. Verify ≤2 calls
3. Copy function body to each call site
4. Adapt variable names to local context
5. Delete original function
6. Run tests

```python
# Before
def get_full_name(user):
    return f"{user.first} {user.last}"

name = get_full_name(user)

# After
name = f"{user.first} {user.last}"
```

---

## 2. Early Return

**When**: Deep nesting > 3 levels

**Steps**:
1. Identify the deepest nesting
2. Invert outer conditions to early returns
3. Remove else branches
4. Flatten remaining code
5. Run tests

```python
# Before
def process(data):
    if data:
        if data.valid:
            if data.ready:
                return transform(data)
    return None

# After
def process(data):
    if not data:
        return None
    if not data.valid:
        return None
    if not data.ready:
        return None
    return transform(data)
```

---

## 3. Extract Then Inline

**When**: Code is tangled, need to understand before simplifying

**Steps**:
1. Extract small pieces into named functions
2. Run tests (verify extraction is correct)
3. Now you can see the structure
4. Inline the unnecessary extractions
5. Keep only genuinely useful functions
6. Run tests

This is "refactor to understand" - temporary complexity to achieve simplicity.

---

## 4. Replace Inheritance with Composition

**When**: Inheritance used for code reuse, not polymorphism

**Steps**:
1. Identify what the subclass actually uses from parent
2. Extract that into a standalone function or small class
3. Have subclass use it directly (composition)
4. Remove inheritance
5. Run tests

```python
# Before: Inheritance for code reuse
class BaseHandler:
    def log(self, msg):
        print(f"[{self.name}] {msg}")

class UserHandler(BaseHandler):
    name = "user"
    def handle(self, data):
        self.log("handling")
        ...

# After: Composition
def log(name, msg):
    print(f"[{name}] {msg}")

class UserHandler:
    def handle(self, data):
        log("user", "handling")
        ...
```

---

## 5. Collapse Hierarchy

**When**: AbstractBase → ConcreteBase → Implementation with one implementation

**Steps**:
1. Verify only one concrete implementation exists
2. Move all non-abstract methods to the implementation
3. Inline abstract method implementations
4. Delete abstract base classes
5. Update all type hints/imports
6. Run tests

---

## 6. Replace Conditional with Guard Clauses

**When**: Long if-else chains for validation

**Steps**:
1. Identify validation/precondition checks
2. Convert each to early return
3. Put happy path at the end, unindented
4. Run tests

```python
# Before
def withdraw(account, amount):
    if account.active:
        if amount > 0:
            if account.balance >= amount:
                account.balance -= amount
                return True
            else:
                return False
        else:
            return False
    else:
        return False

# After
def withdraw(account, amount):
    if not account.active:
        return False
    if amount <= 0:
        return False
    if account.balance < amount:
        return False

    account.balance -= amount
    return True
```

---

## 7. Remove Dead Code

**When**: Code that's never executed

**Steps**:
1. Identify suspected dead code
2. Grep for ALL references: `grep -r "function_name" .`
3. Check for dynamic calls: `getattr`, reflection, string-based lookup
4. Check for external callers (if library/API)
5. If truly dead: delete
6. Run tests
7. If tests fail: code wasn't dead, revert

**Warning**: Be thorough. "Unused" code might be called dynamically.

---

## 8. Simplify Conditional

**When**: Complex boolean expressions

**Steps**:
1. Extract each condition to a well-named variable
2. Combine using clear logic
3. Consider truth table to simplify
4. Run tests

```python
# Before
if (user.role == "admin" or user.role == "superuser") and not user.suspended and (user.verified or user.trust_score > 100):
    allow()

# After
is_privileged = user.role in ("admin", "superuser")
is_active = not user.suspended
is_trusted = user.verified or user.trust_score > 100

if is_privileged and is_active and is_trusted:
    allow()
```

---

## Safety Checklist

Before ANY refactoring:

- [ ] Tests exist and pass
- [ ] You understand what the code does
- [ ] You've grepped all usages

After EACH refactoring step:

- [ ] Tests still pass
- [ ] Behavior unchanged
- [ ] Code is simpler (fewer lines, less nesting, clearer names)

If tests fail:

- [ ] Revert immediately
- [ ] Understand why
- [ ] Try smaller step
