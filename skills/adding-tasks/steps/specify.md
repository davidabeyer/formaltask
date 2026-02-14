---
consumes: [discovered-paths]
produces: [task-spec]
---
# Phase 4: Specify

**BLOCKING GATE:** Paths validated in Phase 3.

## Title

Action verb + specific scope. Bad: "Update tests". Good: "Migrate mutation testing to pytest-mutmut"

## Acceptance Criteria

**REJECT these vague patterns:**
```
properly, correctly, well, good, clean, improved, better,
appropriate, suitable, handles errors, is robust, is efficient,
works correctly, handles edge cases, is maintainable, follows best practices
```

**ACCEPT specific, testable criteria:**
```
Returns 400 status on invalid email format
Logs error with correlation ID on database timeout
Function handles empty list without raising
Response time <200ms for 1000 records
```

Every criterion must be binary testable. If you can't write a test for it, rewrite it.

## Exit Criteria

Title with action verb. At least 2 testable criteria.
