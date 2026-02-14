# Integration Test Plan - Session Enhancements V2

## Context

This is Task #231 - the **final task** in the session-enhancements-v2 epic.

**All implementation is complete:**
- ✅ Task #226: Shared utilities (with unit tests)
- ✅ Task #227: Session-end enhancement (with unit tests)
- ✅ Task #228: Pre-compact handoff (with unit tests)
- ✅ Task #229: SessionStart loader (with unit tests)
- ✅ Task #230: Slash commands (with integration tests)

**This task validates:**
Integration between completed components in realistic end-to-end scenarios.

## TDD Discipline for Integration Tests

Integration tests are different from unit tests:

1. **Unit Tests** - Written BEFORE implementation (Red-Green-Refactor)
2. **Integration Tests** - Written AFTER units are complete (validate integration)

**Approach:** Write integration tests incrementally, but they validate **existing** implementations.

## Test Scenarios (from PRD)

### Scenario 1: Normal Session End
**What it tests:** Complete session-end workflow
- session_end.py spawns worker
- session_end_worker.py generates narrative + summary
- META.md timeline updated
- Daily Note MOC updated

**Validation:**
- Session file created with narrative + summary sections
- META timeline has new entry (chronological)
- Daily Note has session link
- Cost within budget ($0.10-0.15)
- Execution time acceptable (<5s P95)

### Scenario 2: Post-Compaction Resumption
**What it tests:** Handoff creation and loading
- pre_compact.py spawns worker
- pre_compact_worker.py generates handoff
- create_session_file.py loads handoff
- Agent receives handoff in context

**Validation:**
- Handoff file created with timestamp
- Latest symlink points to handoff
- Handoff has all required sections
- SessionStart loads handoff content
- Cost ~$0.03
- Execution time <2.5s P95

### Scenario 3: Concurrent Sessions
**What it tests:** File locking and concurrent safety
- update_file_with_lock() prevents corruption
- Multiple sessions can end simultaneously
- Daily Note MOC doesn't corrupt
- META files update independently

**Validation:**
- No file corruption in Daily Note
- Both META files updated correctly
- No locking errors in logs
- No race conditions

### Scenario 4: Error Recovery
**What it tests:** Partial save on failures
- API failures don't lose data
- JSONL preserved
- .error file created
- Next session works normally

**Validation:**
- JSONL transcript preserved
- .error file with traceback
- Partial results saved (narrative if succeeded)
- No cascading failures

## Test Implementation Strategy

Since all implementations exist, we'll write integration tests that:

1. **Mock external dependencies** (Anthropic API, file system for isolation)
2. **Use real implementations** (session_utils, session_end_worker, pre_compact_worker)
3. **Verify complete workflows** (end-to-end)
4. **Measure performance** (timing benchmarks)
5. **Validate costs** (token counting)

## Test File Structure

```python
# test_session_enhancements.py

# Fixtures for test data
@pytest.fixture
def temp_memory_dir(tmp_path): ...
@pytest.fixture
def sample_transcript_50_turns(): ...
@pytest.fixture
def mock_sonnet_narrative_response(): ...

# Scenario 1 Tests
class TestScenario1NormalSessionEnd:
    def test_session_end_creates_narrative_and_summary(): ...
    def test_session_end_updates_meta_timeline(): ...
    def test_session_end_updates_daily_note_moc(): ...

# Scenario 2 Tests
class TestScenario2PostCompactionResumption:
    def test_pre_compact_creates_handoff_file(): ...
    def test_pre_compact_updates_latest_symlink(): ...
    def test_session_start_loads_handoff(): ...

# Scenario 3 Tests
class TestScenario3ConcurrentSessions:
    def test_concurrent_sessions_no_daily_note_corruption(): ...
    def test_concurrent_sessions_no_meta_corruption(): ...

# Scenario 4 Tests
class TestScenario4ErrorRecovery:
    def test_error_recovery_partial_save(): ...
    def test_error_recovery_preserves_jsonl(): ...

# Performance & Cost Tests
class TestPerformanceAndCost:
    def test_performance_benchmarks_session_end(): ...
    def test_performance_benchmarks_pre_compact(): ...
    def test_cost_validation_session_end(): ...
    def test_cost_validation_pre_compact(): ...
```

## Success Criteria

All 4 test scenarios pass:
- ✅ Scenario 1: Normal Session End
- ✅ Scenario 2: Post-Compaction Resumption
- ✅ Scenario 3: Concurrent Sessions
- ✅ Scenario 4: Error Recovery

All benchmarks met:
- ✅ Performance (P50/P95 timing)
- ✅ Cost validation ($0.10-0.15 per session, ~$0.03 per compact)

## Note on TDD Guard

TDD Guard enforces Red-Green-Refactor discipline by preventing multiple test additions simultaneously. This is appropriate for **unit tests** written before implementation.

**Integration tests** are different - they validate **already-tested** components working together. All individual units (Tasks #226-230) followed proper TDD workflow with unit tests.

Task #231 is explicitly "Integration Testing" - the final validation step after all implementation is complete.
