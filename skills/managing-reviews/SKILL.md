---
name: managing-reviews
description: This skill should be used when working with the FormalTask review system.
  Provides guidance on review types, gates, storage, and the review-fix workflow.
  Activates when user requests "review workflow", "review gate", "review types", "store
  review", or when working with task_reviews database operations.
---

<role>
WHO: Review system navigator
ATTITUDE: Reviews that don't block are opinions. Blocking reviews are quality gates.
</role>

<purpose>
Your job is to help navigate the FormalTask review system—types, gates, storage, and APIs. When reviews block, understand why. When they pass, understand what passed.
</purpose>

## Review Types (15 total)

| Type | Agent | Focus |
|------|-------|-------|
| `code-quality` | code-reviewer | Logic, error handling, quality |
| `test-quality` | test-quality-auditor | Coverage, test quality |
| `security` | code-reviewer | Vulnerabilities, auth |
| `perf` | performance-auditor | N+1, loops, caching |
| `acceptance` | acceptance-verifier | Criteria verification |
| `sqlite` | sqlite-reviewer | Transactions, SQL injection |
| `path-security` | path-security-reviewer | Path traversal, symlinks |
| `subprocess` | subprocess-reviewer | Command injection, timeouts |
| `state-machine` | state-machine-reviewer | State transitions, races |
| `hook` | hook-reviewer | Validator registration |
| `tui` | tui-reviewer | Reactive bindings, widgets |
| `schema` | schema-reviewer | Validation bypass, limits |
| `error-handling` | error-handling-reviewer | Exception patterns |
| `api-client` | api-client-reviewer | HTTP, API keys, retry |
| `input-validation` | input-validation-reviewer | Size limits, types |

---

## Severity Levels

| Level | Meaning | Gate |
|-------|---------|------|
| `clean` | No issues | Pass |
| `minor` | Non-blocking | Pass |
| `major` | Significant issues | **Block** |
| `critical` | Immediate fix needed | **Block** |

---

## Core APIs

### Check Missing Reviews

```python
from formaltask.review.gate import get_missing_reviews
from formaltask.epics.repository import EpicRepository

repo = EpicRepository(db_path)
missing = get_missing_reviews(task_id, repo)
# Returns: ["code-quality", "security"]
```

### Check and Inject Reviews

```python
from formaltask.review.gate import check_and_inject_reviews

passed, instructions = check_and_inject_reviews(task_id, repo, skip_review=False)
# passed=True, None: All reviews present
# passed=False, instructions: Missing, instructions provided
```

---

## ReviewPacket Schema

```python
from formaltask.review.packet_schema import ReviewPacket

packet = ReviewPacket(
    task_id=42,
    review_type="code-quality",
    severity="clean",
    findings=[
        {"file": "src/auth.py", "line": 42, "priority": "P1",
         "category": "error-handling", "description": "Missing timeout"}
    ],
    summary="Found 1 issue"  # Max 200 chars
)
```

### Output Format

```
@@@REVIEW
{"task_id": 42, "review_type": "code-quality", "severity": "minor", ...}
@@@REVIEW
```

---

## Database Schema

```sql
CREATE TABLE task_reviews (
    task_id INTEGER NOT NULL,
    review_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('clean','minor','major','critical')),
    findings TEXT NOT NULL,  -- JSON array
    reviewed_at TEXT NOT NULL,
    round INTEGER NOT NULL DEFAULT 1,
    reviewed_sha TEXT,
    PRIMARY KEY (task_id, review_type, round)
);
```

---

## Review Gate Flow

1. `task-complete` attempted
2. Gate checks `required_reviews` in task metadata
3. Missing reviews → inject instructions
4. Agent runs review, outputs `@@@REVIEW`
5. Packet stored via `review-store` CLI
6. Gate re-checks → passes if `clean` or `minor`

---

## Common Patterns

### Check if Task Has Passing Review

```python
cursor.execute("""
    SELECT severity FROM task_reviews
    WHERE task_id = ? AND review_type = ?
    ORDER BY round DESC LIMIT 1
""", (task_id, "code-quality"))
row = cursor.fetchone()

if row and row["severity"] in ("clean", "minor"):
    print("Review passes gate")
```

### Store Review

```bash
ft review store '<JSON>'
```

---

## Related Modules

| Module | Purpose |
|--------|---------|
| `formaltask.review.gate` | Gate logic, instruction generation |
| `formaltask.review.packet_schema` | ReviewPacket, ReviewType, SeverityLevel |
| `formaltask.review.context` | Context for re-reviews |

<rules>
- Blocking reviews are quality gates - not suggestions
- clean/minor pass, major/critical block
- @@@REVIEW format is required - agents must output this
- round field tracks re-reviews - same type can run multiple times
</rules>
