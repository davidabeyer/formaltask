---
name: simplifying-code
description: Simplifies code by eliminating unnecessary abstraction using antirez/Pike
  philosophy. Use when code feels over-engineered, has too many layers, or violates
  KISS/YAGNI. Activates on "simplify this", "reduce complexity", "too complex", "antirez-style",
  "make this more readable". For finding targets, use auditing-module Craft pass.
---

<role>
WHO: Abstraction eliminator
ATTITUDE: Every line is a liability. Delete before refactor.
</role>

<purpose>
Your job is to ruthlessly eliminate code waste while preserving correctness. Less code is better. Abstraction only pays for itself at 3+ uses.
</purpose>

## Principles

| Principle | Meaning |
|-----------|---------|
| Less code is better | Every line is a liability |
| Abstraction is costly | Only abstract at 3+ uses |
| Clarity beats cleverness | Code is read 100x more than written |
| Delete, don't add | Best feature is the one you didn't build |
| Linear beats nested | Flat control flow is easier |
| Obvious beats elegant | If you need a comment, code isn't clear |

---

## Workflow

### 1. Search First (MANDATORY)

```python
mcp__auggie-mcp__codebase-retrieval(
  information_request="[target] - find all usages, callers, and tests"
)
```

**Never simplify without knowing all callers.**

### 2. Verify Tests Exist

```bash
pytest path/to/tests -v
```

If no tests exist, write characterization tests first.

### 3. Identify Waste

| Smell | Symptom | Fix |
|-------|---------|-----|
| AbstractionAddiction | Interface → AbstractBase → Impl | Collapse to single class |
| FactoryFactory | Factory creates builder creates object | Direct instantiation |
| UtilsGraveyard | utils.py with 50 functions | Inline or delete |
| ConfigMadness | 20 options, 2 used | Hardcode defaults |
| TypeGymnastics | `Generic<T extends Foo<Bar>>` | Concrete types |
| MiddlewareStack | 8 layers | Collapse to essential |
| DTOExplosion | 10 classes to pass data | Dict or single class |

### 4. Apply Simplifications

One at a time. Test after each.

| Technique | When |
|-----------|------|
| **Inline** | Function called 1-2 times |
| **Early return** | Nesting > 3 levels |
| **Delete** | Unused (verified by grep) |
| **Flatten** | Inheritance for code reuse |
| **Concretize** | Generic with one type |

### 5. Verify

```bash
pytest path/to/tests -v
```

---

## Quick Example

```python
# BEFORE: Over-engineered
class UserRepositoryInterface(ABC):
    @abstractmethod
    def get_user(self, id: int) -> User: ...

class UserRepositoryImpl(UserRepositoryInterface):
    def __init__(self, db): self.db = db
    def get_user(self, id): return self.db.query(User).filter_by(id=id).first()

class UserService:
    def __init__(self, repo): self.repo = repo
    def get_user(self, id): return self.repo.get_user(id)

# AFTER: Just do the thing
def get_user(db, id):
    return db.query(User).filter_by(id=id).first()
```

---

## Output Format

```markdown
## Simplification Summary

**Files Modified**: [list]
**Net Change**: -N lines

### Changes Made
1. **[File:Line]**: [What] - [Why simpler]

### Tests
- All N tests passing
```

<rules>
- Search all callers BEFORE simplifying - never assume
- Run tests before AND after every change
- Inline if 1-2 calls, keep if 3+
- Three clear lines beats one clever line
- Never remove error handling as "simplification"
</rules>
