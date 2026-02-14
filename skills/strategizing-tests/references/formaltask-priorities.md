# FormalTask Hypothesis Priority Matrix

Module-by-module analysis of `hooks/lib/` for property-based testing.

## P0: High-Value Targets (Start Here)

| Module | Property Type | Why |
|--------|---------------|-----|
| `epic_parser.py` | Roundtrip | Parse markdown -> create epic.md -> parse again |
| `validation_schemas.py` | Invariant | Valid inputs always accepted, invalid rejected |
| `schemas.py` | Roundtrip | Pydantic model -> JSON -> back to model |
| `metadata_schemas.py` | Roundtrip | Session metadata JSON roundtrip |
| `stub_detector.py` | Invariant | Real code never detected as stub |

## P1: Medium-Value Targets

| Module | Property Type | Why |
|--------|---------------|-----|
| `task_guards.py` | State Machine | Dependency satisfaction logic |
| `session_utils.py` | Idempotence | File locking, update operations |
| `metadata_utils.py` | Idempotence | Consumer position tracking |
| `gh_cli.py` | Invariant | Command building produces valid CLI |

## P2: Lower-Value Targets

| Module | Notes |
|--------|-------|
| `epic_repository.py` | Database ops - use integration tests |
| `gemini_client.py` | External API - mock in example tests |
| `github_simple_sync.py` | Already has property tests! |

## Skip for Property Testing

- `db_connection.py` - Infrastructure, not logic
- `worker_monitor.py` - Concurrency (needs different testing)
- Validators that call external services

## Implementation Order

1. **Create strategies file** (`hooks/tests/strategies/formaltask_strategies.py`)
2. **P0 Property tests:**
   - `test_epic_parser_properties.py` (roundtrip)
   - `test_schemas_properties.py` (roundtrip)
   - `test_validation_schemas_properties.py` (invariant)
3. **P1 Property tests:**
   - `test_task_guards_properties.py` (state machine)
   - `test_session_utils_properties.py` (idempotence)
4. **Add to CI** with reasonable `max_examples` (50-100)

## Coverage Optimization

1. **Property tests cover edge cases automatically** - One property test = 100+ example tests
2. **Focus example tests on happy paths** - Property tests find edge cases
3. **Integration tests for cross-module flows** - Not suited for Hypothesis

## Risk-Based Priority

| Priority | Category | Examples |
|----------|----------|----------|
| P0 | Security | Authentication, authorization, input sanitization |
| P0 | Data integrity | Database ops, serialization, parsing |
| P0 | Financial | Payments, credits, transactions |
| P1 | Core workflows | Epic/task lifecycle, GitHub sync |
| P1 | User-facing | CLI commands, status reporting |
| P2 | Edge cases | Error handling, boundary conditions |
| P2 | Nice-to-have | Formatting, display logic |
