# Deep Analysis Quality Criteria

Six criteria for evaluating code quality. Read ALL code before applying.

---

## Criterion 1: Simplicity

**Question:** Does each function have a single responsibility?

| NOT a violation | ACTUAL violation |
|-----------------|------------------|
| Long function where every line serves one goal | Function that parses AND validates AND persists |
| Multiple related steps in sequence (workflow) | Class mixing business logic AND infrastructure |

---

## Criterion 2: Clarity

**Question:** Can you understand each function in 2 minutes?

| NOT a violation | ACTUAL violation |
|-----------------|------------------|
| Long but straightforward function | Clever one-liner taking 5 min to parse |
| Deep nesting reflecting problem structure | Unclear control flow, obscure names |

---

## Criterion 3: Data Visibility

**Question:** Can you see what data exists and its state?

| NOT a violation | ACTUAL violation |
|-----------------|------------------|
| Encapsulation protecting invariants | Data scattered across 10 objects |
| Private fields with good reason | Chain of getters hiding simple values |

---

## Criterion 4: Necessity (YAGNI)

**Question:** Does each abstraction earn its existence?

| NOT a violation | ACTUAL violation |
|-----------------|------------------|
| ABC with 3+ implementations | ABC with exactly 1 implementation |
| Interface enabling testing | 5-layer indirection for simple operation |

---

## Criterion 5: Test Honesty

**Question:** Do tests verify what they claim?

| NOT a violation | ACTUAL violation |
|-----------------|------------------|
| Missing edge cases (incomplete, not dishonest) | `test_validates_X` with no validation assertion |
| Tests that mock dependencies (often necessary) | Test that mocks the thing it's testing |

---

## Criterion 6: Liveness

**Question:** Is all code reachable?

```bash
# Find callers - 0 results outside definition/tests = dead
grep -r "function_name\\(" --include="*.py" | grep -v __pycache__ | grep -v test
```

---

## Finding Format

Every finding MUST include:

```markdown
### Finding: {title}
**Location:** `{file}:{lines}`
**Criterion:** {which one}
**Severity:** Critical | Significant | Minor

**Current code:**
```python
{5+ lines of context}
```

**The problem:** {specific, not "could be better"}

**Proposed fix:**
```python
{improved code}
```

**Why better:** {concrete reason}
```
