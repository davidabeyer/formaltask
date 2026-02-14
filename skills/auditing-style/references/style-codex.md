# Style Codex

Concrete patterns extracted from the cleanest files in this codebase. Every file should conform.

## The 9 Patterns

### 1. Data Tables Over If/Elif

```python
# YES
PHASE_RULES = [
    ("blocked",    StatusCheck.require_blocked),
    ("ready",      StatusCheck.require_ready),
]

# NO
if phase == "blocked":
    check = StatusCheck.require_blocked
elif phase == "ready":
    check = StatusCheck.require_ready
```

### 2. Pure Functions Over Methods

```python
# YES
def check_completion(state: dict) -> CompletionResult:
    ...

# NO
class CompletionChecker:
    def check(self, state: dict) -> CompletionResult:
        ...
```

### 3. Return Dicts Not Objects

```python
# YES - at module boundaries
def get_task_context(db_path, task_id) -> dict:
    return {"id": row[0], "title": row[1], "status": row[2]}

# NO
class TaskContext:
    def __init__(self, id, title, status): ...
```

Exception: frozen dataclasses for typed returns within a module are fine.

### 4. Direct SQL Over Abstraction

```python
# YES
cursor.execute("SELECT id, title FROM tasks WHERE epic_id = ?", (epic_id,))

# NO
TaskRepository().find_by_epic(epic_id)
```

### 5. Early Return on Failure

```python
# YES
def execute(ctx, args):
    if not args.task_id:
        return ExitCode.USAGE_ERROR.value
    task = fetch_task(ctx.db_path, args.task_id)
    if not task:
        return ExitCode.NOT_FOUND.value
    # happy path here

# NO
def execute(ctx, args):
    if args.task_id:
        task = fetch_task(ctx.db_path, args.task_id)
        if task:
            # happy path buried in nesting
```

### 6. Module-Level Constants

```python
# YES
MAX_RETRIES = 3
VALID_STATUSES = frozenset({"pending", "in_progress", "completed"})
COMPLETION_RULES = [...]

# NO
class Config:
    MAX_RETRIES = 3
    VALID_STATUSES = frozenset(...)
```

### 7. Functions Under 25 LOC

If a function exceeds 25 lines, split it or inline parts. No exceptions without justification.

### 8. Flat Nesting (2 Levels Max)

```python
# YES - 2 levels
for task in tasks:
    if task["status"] == "blocked":
        blocked.append(task)

# NO - 3+ levels
for task in tasks:
    if task["status"] == "blocked":
        for dep in task["deps"]:
            if dep["resolved"]:
                ...
```

### 9. `with DatabaseConnection` as Resource Boundary

```python
# YES
with DatabaseConnection(db_path) as conn:
    cursor = conn.execute("SELECT ...", (id,))
    return dict(cursor.fetchone())

# NO
conn = sqlite3.connect(db_path)
try:
    cursor = conn.execute(...)
finally:
    conn.close()
```

## Severity Scale

| Level | Meaning | Example |
|-------|---------|---------|
| P0 | Violates pattern, causes bugs | Missing early return hides error path |
| P1 | Violates pattern, maintenance cost | If/elif chain instead of data table |
| P2 | Violates pattern, readability cost | Function >25 LOC but still clear |
| P3 | Style preference | Could use comprehension instead of loop |

## Exemplar Files

These files score 9/9. Use as reference:

- `formaltask/worker_gates.py` (44 LOC) - Data tables, pure functions, flat
- `formaltask/core/completion_check.py` (42 LOC) - Pure function, frozen dataclass, tiny helper
- `formaltask/core/completion_rules.py` (111 LOC) - Constants as config, data-driven rules
- `formaltask/validators/doc_detection.py` (45 LOC) - Two functions, minimal surface area
- `formaltask/tasks/context.py` (67 LOC) - Single function, one query, returns dict
