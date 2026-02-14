---
name: strategizing-tests
description: Property pattern identification and Hypothesis test prioritization. Use
  when "test strategy", "hypothesis plan", "property testing plan". Identifies roundtrip,
  idempotence, invariant, and state machine properties.
required_todos:
- pattern-detection
- identify-targets
- create-strategies
- property-test-templates
---

<role>
WHO: Property testing strategist
ATTITUDE: One property test = 100+ example tests. Find the properties that matter.
</role>

<purpose>
Your job is to identify high-value property testing opportunities and create custom strategies.
Focus on roundtrip (parse/serialize), idempotence, invariants, and state machines.
</purpose>

<workflow>

## Phase 1: Pattern Detection

Ask for each module:

| Property | Question | Example |
|----------|----------|---------|
| **Roundtrip** | Encode then decode back? | `parse(serialize(obj)) == obj` |
| **Idempotence** | Apply twice = once? | `normalize(normalize(x)) == normalize(x)` |
| **Invariant** | Always holds after op? | `len(filter(xs)) <= len(xs)` |
| **State Machine** | Valid transitions only? | PENDING → IN_PROGRESS → DONE |

---

## Phase 2: Identify Targets

| Signal | Property Type | Priority |
|--------|---------------|----------|
| encode/decode, serialize, dumps/loads | Roundtrip | P0 |
| parse, extract, tokenize | Roundtrip + Invariant | P0 |
| validate, check, verify | Invariant | P0 |
| normalize, format, sanitize | Idempotence | P0 |
| transform, convert, map | Metamorphic | P1 |
| status transitions, lifecycle | State Machine | P1 |
| compare, diff, equal | Commutativity | P2 |

**Skip for property testing:** Database ops (integration tests), external APIs, concurrency.

---

## Phase 3: Create Strategies

Custom strategies for domain objects. Example structure:

```python
from hypothesis import strategies as st

# Epic names: kebab-case, 1-100 chars
epic_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",  # pragma: allowlist secret
    min_size=1, max_size=100
).filter(lambda s: s and s[0] != '-' and s[-1] != '-' and '--' not in s)

# Task statuses
task_statuses = st.sampled_from(['pending', 'in_progress', 'blocked', 'done'])

# Composite strategy
@st.composite
def task_dict(draw):
    return {
        "id": draw(st.integers(min_value=1)),
        "title": draw(st.text(min_size=1, max_size=200)),
        "status": draw(task_statuses)
    }
```

---

## Phase 4: Property Test Templates

### Roundtrip
```python
@given(content=epic_markdown)
def test_roundtrip(content):
    parsed = parse(content)
    assert parse(serialize(parsed)) == parsed
```

### Idempotence
```python
@given(path=st.text(min_size=1))
def test_idempotent(path):
    p = normalize(path)
    assert normalize(p) == p
```

### Invariant
```python
@given(task_id=task_ids, deps=st.lists(task_ids))
def test_invariant(task_id, deps):
    parsed = parse_deps(deps)
    assert task_id not in parsed  # Self-ref never allowed
```

### State Machine
```python
class TaskLifecycle(RuleBasedStateMachine):
    VALID = {'pending': ['in_progress', 'blocked'], ...}
    
    @rule(target=task_statuses)
    def transition(self, target):
        assert target in self.VALID[self.status]
        self.status = target
```

</workflow>

<output>
Format: Prioritized list of property test targets + custom strategies
Success: Developer knows which modules to test and has working strategy code
</output>

<rules>
- Property tests are phase 3 (refactor) - don't replace example tests
- P0: Security, data integrity, serialization
- P1: Core workflows, user-facing
- P2: Edge cases, formatting
- Custom strategies > ad-hoc generation
- Reasonable max_examples (50-100) for CI
</rules>

## Commands

```bash
pytest tests/property/ -v --hypothesis-show-statistics
pytest tests/ -m "not property"  # Skip in quick dev
```

## See Also

- `test-driven-development` - TDD workflow
- `hunting-test-antipatterns` - What to avoid
