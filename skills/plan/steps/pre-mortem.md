---
consumes: [goal, discovery-results]
produces: [risk-analysis]
optional: true
---
## Phase 4: Run Pre-mortem (full only)

Assume the project failed. Why?
- Technical risks (bottlenecks, race conditions, API limits)
- Edge cases (empty input, network failure, concurrent requests)
- Security (input validation, auth, injection)
- State completeness (replacement function return keys, field mappings, ordering behavior)

**EXIT CRITERIA:** At least 3 failure modes identified with mitigations.
