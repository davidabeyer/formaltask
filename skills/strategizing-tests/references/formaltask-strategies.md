# FormalTask Hypothesis Strategies

Custom Hypothesis strategies for FormalTask domain objects and property test templates.

## Strategy Library

Create in `hooks/tests/strategies/formaltask_strategies.py`:

```python
from hypothesis import strategies as st
from datetime import datetime

# Epic names: kebab-case, 1-100 chars
epic_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=100
).filter(lambda s: s and s[0] != '-' and s[-1] != '-' and '--' not in s)

# Task titles: 1-200 chars, no control characters
task_titles = st.text(min_size=1, max_size=200).filter(
    lambda s: s.strip() and not any(c < ' ' for c in s)
)

# Task status (enum values)
task_statuses = st.sampled_from(['pending', 'in_progress', 'blocked', 'deferred', 'done'])

# Task IDs (positive integers)
task_ids = st.integers(min_value=1, max_value=10000)

# Dependency lists (valid task ID references)
def dependencies(existing_ids: list[int]):
    return st.lists(st.sampled_from(existing_ids), unique=True) if existing_ids else st.just([])

# Acceptance criteria: list of strings
acceptance_criteria = st.lists(
    st.text(min_size=1, max_size=500).filter(lambda s: s.strip()),
    min_size=1,
    max_size=10
)

# Session IDs: UUID-like format
session_ids = st.uuids().map(str)

# ISO timestamps
timestamps = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31)
).map(lambda dt: dt.isoformat())

# Epic markdown content
@st.composite
def epic_markdown(draw):
    name = draw(epic_names)
    desc = draw(st.text(min_size=10, max_size=500))
    n_tasks = draw(st.integers(min_value=1, max_value=10))

    tasks = []
    for i in range(n_tasks):
        title = draw(task_titles)
        criteria = draw(acceptance_criteria)
        criteria_md = "\n".join(f"- [ ] {c}" for c in criteria)
        tasks.append(f"### Task {i+1}: {title}\n\n{criteria_md}")

    return f"# Epic: {name}\n\n{desc}\n\n## Tasks\n\n" + "\n\n".join(tasks)

# Pydantic-compatible dicts for schemas
@st.composite
def next_step_dict(draw):
    return {
        "step": draw(st.text(min_size=1, max_size=200)),
        "priority": draw(st.sampled_from(["P0", "P1", "P2"])),
        "confidence": draw(st.sampled_from(["high", "medium", "low"])),
        "estimated_effort": draw(st.sampled_from(["minutes", "hours", "days"])),
        "dependencies": draw(st.text(max_size=200))
    }

@st.composite
def blocker_dict(draw):
    return {
        "issue": draw(st.text(min_size=1, max_size=300)),
        "impact": draw(st.text(min_size=1, max_size=300)),
        "attempted_solutions": draw(st.text(max_size=500)),
        "needs": draw(st.text(min_size=1, max_size=300))
    }

@st.composite
def file_change_dict(draw):
    return {
        "file": draw(st.text(min_size=1, max_size=200)),
        "description": draw(st.text(min_size=1, max_size=500))
    }
```

## Property Test Templates

### Roundtrip Template

```python
from hypothesis import given
import hypothesis.strategies as st

# Define epic markdown strategy
epic_markdown = st.text(min_size=10, max_size=1000)

@given(content=epic_markdown)
def test_epic_parser_roundtrip(content):
    """Property: Parse epic → serialize → parse produces same result"""
    from formaltask.epics.parser import parse_epic_file

    # Illustrative example - adapt to actual parser API
    parsed1 = parse_epic_file(content)
    # serialized = serialize_epic(parsed1)
    # parsed2 = parse_epic_file(serialized)
    # assert parsed1.tasks == parsed2.tasks
```

### Idempotence Template

```python
from hypothesis import given
import hypothesis.strategies as st
from pathlib import Path

@given(path=st.text(min_size=1, max_size=500))
def test_path_resolve_idempotent(path):
    """Property: Resolving a path twice equals resolving once"""
    try:
        p = Path(path).expanduser().resolve()
        assert p.resolve() == p
    except (OSError, ValueError):
        pass  # Invalid paths are expected
```

### Invariant Template

```python
from hypothesis import given
import hypothesis.strategies as st

# Strategies for task testing
task_statuses = st.sampled_from(["open", "active", "completed", "cancelled"])
task_ids = st.integers(min_value=1, max_value=1000)

@given(task_id=task_ids, deps=st.lists(task_ids, max_size=5))
def test_dependency_parsing_never_includes_self(task_id, deps):
    """Property: Parsed dependencies should never include self-reference"""
    from formaltask.db.helpers import parse_depends_on
    import json

    # Build dependency JSON excluding self
    valid_deps = [d for d in deps if d != task_id]
    deps_json = json.dumps(valid_deps)

    parsed = parse_depends_on(deps_json)
    assert task_id not in parsed
```

### State Machine Template

```python
from hypothesis import given
from hypothesis.stateful import RuleBasedStateMachine, rule, Bundle
import hypothesis.strategies as st

# Define task statuses strategy inline
task_statuses = st.sampled_from(["open", "active", "completed", "cancelled"])

class TaskLifecycleStateMachine(RuleBasedStateMachine):
    """Property: Task status transitions follow valid lifecycle"""

    VALID_TRANSITIONS = {
        'pending': ['in_progress', 'blocked', 'deferred'],
        'in_progress': ['blocked', 'done', 'pending'],
        'blocked': ['pending', 'deferred'],
        'deferred': ['pending'],
        'done': []  # Terminal state
    }

    def __init__(self):
        super().__init__()
        self.status = 'pending'

    @rule(target=task_statuses)
    def transition(self, target):
        valid = target in self.VALID_TRANSITIONS[self.status]
        if valid:
            self.status = target
        return target

TestTaskLifecycle = TaskLifecycleStateMachine.TestCase
```
