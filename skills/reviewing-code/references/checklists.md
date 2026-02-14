# Code Review Checklists

Detailed checklists for systematic code review. Apply each section to code under review.

---

## Checklist 1: Logic Correctness

### Control Flow
- [ ] All branches are reachable (no dead code)
- [ ] Loop termination is guaranteed (no infinite loops)
- [ ] Recursion has proper base cases
- [ ] Switch/match statements handle all cases (including default)
- [ ] Early returns don't skip required cleanup

### Data Flow
- [ ] Variables are initialized before use
- [ ] No unintended variable shadowing
- [ ] Mutable state changes are intentional
- [ ] No use-after-free or dangling references
- [ ] Closures capture variables correctly

### Boundary Conditions
- [ ] Off-by-one errors checked (< vs <=, index bounds)
- [ ] Empty collections handled (empty list, null, undefined)
- [ ] Zero/negative numbers handled where applicable
- [ ] Maximum values don't cause overflow
- [ ] String operations handle empty/whitespace strings

---

## Checklist 2: Error Handling

### Exception Management
- [ ] Errors are caught at appropriate levels
- [ ] No empty catch blocks (silent failures)
- [ ] Specific exceptions caught (not bare `except:` or `catch (Exception)`)
- [ ] Error messages are descriptive and actionable
- [ ] Stack traces preserved when re-throwing

### Failure Modes
- [ ] Network failures handled (timeouts, connection errors)
- [ ] File system failures handled (permissions, disk full)
- [ ] Database failures handled (connection loss, deadlock)
- [ ] External API failures handled (rate limits, invalid responses)
- [ ] Partial failures handled (some operations succeed, others fail)

### Resource Cleanup
- [ ] Resources released in finally/defer/with blocks
- [ ] Database connections closed
- [ ] File handles closed
- [ ] Temporary files cleaned up
- [ ] Event listeners unsubscribed

---

## Checklist 3: Edge Cases

### Input Validation
- [ ] Null/undefined inputs handled
- [ ] Empty strings handled
- [ ] Invalid types handled (or type-checked)
- [ ] Malformed data handled (invalid JSON, corrupt files)
- [ ] Extremely large inputs handled (or bounded)

### Concurrency
- [ ] Race conditions prevented (locks, atomic operations)
- [ ] Deadlock potential analyzed
- [ ] Thread-safe data structures used where needed
- [ ] Async operations awaited correctly
- [ ] No shared mutable state without synchronization

### State Management
- [ ] State transitions are valid
- [ ] Invalid states are unreachable
- [ ] State is consistent after errors
- [ ] Idempotency where expected (retry-safe operations)
- [ ] Rollback works correctly on failure

---

## Checklist 4: API Design

### Function Signatures
- [ ] Parameters are in logical order
- [ ] Default values are sensible
- [ ] Return types are consistent
- [ ] Side effects are documented
- [ ] Function does one thing (single responsibility)

### Contracts
- [ ] Preconditions documented and enforced
- [ ] Postconditions are met
- [ ] Invariants maintained
- [ ] Error conditions documented
- [ ] Nullability is explicit

### Backwards Compatibility
- [ ] Public API changes are intentional
- [ ] Deprecations use proper warnings
- [ ] Breaking changes are documented
- [ ] Migration path provided for breaking changes

---

## Checklist 5: Code Quality

### Readability
- [ ] Variable names are descriptive
- [ ] Function names describe what they do
- [ ] Complex logic has explanatory comments
- [ ] Magic numbers are named constants
- [ ] Code structure matches mental model

### Maintainability
- [ ] Functions are <50 lines (generally)
- [ ] Cyclomatic complexity is reasonable
- [ ] No deep nesting (>3 levels)
- [ ] DRY principle followed (no copy-paste)
- [ ] Single responsibility principle followed

### Documentation
- [ ] Public APIs have docstrings
- [ ] Complex algorithms are explained
- [ ] Non-obvious decisions documented
- [ ] TODO/FIXME have linked issues
- [ ] README updated if needed

---

## Checklist 6: Testing

### Coverage
- [ ] Happy path tested
- [ ] Error paths tested
- [ ] Edge cases tested
- [ ] Boundary conditions tested
- [ ] Integration points tested

### Test Quality
- [ ] Tests are deterministic (no flakiness)
- [ ] Tests are isolated (don't depend on each other)
- [ ] Tests have meaningful assertions (not just `expect(true)`)
- [ ] Test names describe the scenario
- [ ] Mocks are used appropriately (not over-mocked)
