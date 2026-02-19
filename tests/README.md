# tests/ - Detailed Documentation

Test infrastructure for hooks and FormalTask. Follows TDD workflow with comprehensive mocking patterns.

## Structure

```
tests/
├── conftest.py             # Core autouse fixtures + backward compatibility re-exports
├── fixtures/               # Modular fixture modules (pytest_plugins)
│   ├── __init__.py         # pytest_plugins list with all 6 modules (complete)
│   ├── database.py         # Database fixtures (Task #1652)
│   ├── mocks.py            # Mock fixtures (Task #1653)
│   ├── accumulated_context.py  # V1/V2 context fixtures (Task #1654)
│   ├── worktree.py         # Worktree session fixtures (Task #1655)
│   ├── connection_tracking.py  # Connection leak detection (Task #1656)
│   ├── pre_compact.py      # Pre-compact worker fixtures (Task #1656)
│   └── helpers.py          # Utility functions (not fixtures) (Task #1656)
├── unit/                   # Unit tests (fast, isolated)
├── integration/            # Integration tests (cross-module, subprocess)
│   ├── test_formaltask_db_guard_integration.py  # Hook JSON protocol tests
│   └── test_worker_lifecycle_e2e.py            # End-to-end worker lifecycle tests
├── property/               # Property-based tests (Hypothesis)
├── lib/                    # Additional test utilities
├── session-end/            # Session-end specific tests
├── pre-compact/            # Pre-compact tests
└── *.py, *.bats            # Root-level tests
```

## Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=formaltask

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_epic_repository_v5.py -v

# Run specific test
pytest tests/unit/test_epic_repository_v5.py::test_create_epic -v

# Coverage report
pytest tests/ -v --cov=formaltask --cov-report=html
open htmlcov/index.html
```

## Key Fixtures (conftest.py)

### Database Fixtures

```python
@pytest.fixture
def db_path(tmp_path):
    """Temporary database with schema loaded."""

@pytest.fixture
def db_with_epic_and_tasks(db_path):
    """Database with test epic and 5 tasks in various states."""

@pytest.fixture
def repo(db_path):
    """Test helper with db_path pre-bound (see tests/fixtures/database.py)."""
```

### Mocking Fixtures

```python
@pytest.fixture
def mock_gh_cli(monkeypatch):
    """Mock GitHub CLI (gh) commands."""

@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess.run for external commands."""
```

### File System

```python
@pytest.fixture
def tmp_path():
    """pytest built-in: Temporary directory for file operations."""

@pytest.fixture
def session_dir(tmp_path):
    """Pre-configured session directory structure."""
```

## Modular Fixtures (fixtures/ directory)

The `fixtures/` directory provides modular fixture organization using pytest_plugins for automatic discovery.

### Structure

```python
# tests/fixtures/__init__.py
pytest_plugins: list[str] = [
    "tests.fixtures.database",              # Database fixtures
    "tests.fixtures.mocks",                 # Mock fixtures
    "tests.fixtures.accumulated_context",   # Accumulated context fixtures
    "tests.fixtures.worktree",              # Worktree session fixtures
    "tests.fixtures.connection_tracking",   # Connection leak detection
    "tests.fixtures.pre_compact",           # Pre-compact worker fixtures
    # Note: helpers.py contains utility functions, not fixtures
]
```

### Migration Strategy

As `conftest.py` grows, extract related fixtures into focused modules:

```python
# Example: Complete structure after all extractions (Task #1656)
pytest_plugins = [
    "tests.fixtures.database",              # db_path, repo, db_with_epic_and_tasks
    "tests.fixtures.mocks",                 # mock_gh_cli, mock_subprocess
    "tests.fixtures.accumulated_context",   # V1/V2 context, corrupt files
    "tests.fixtures.worktree",              # session_dir, worktree_root
    "tests.fixtures.connection_tracking",   # track_connections, mock_db_connection_with_error
    "tests.fixtures.pre_compact",           # pre_compact_main_env, pre_compact_main_mocks
]
```

### Benefits

- **Focused modules**: Group related fixtures (database, mocking, file system)
- **Automatic discovery**: pytest loads all modules in pytest_plugins list
- **Reduced conftest.py**: Keep core configuration, move specialized fixtures
- **Faster imports**: Load only needed fixtures per test module

### Usage

Fixtures from modules in pytest_plugins are available to all tests automatically:

```python
# No explicit imports needed - pytest auto-loads from pytest_plugins
def test_epic_operations(db_path, mock_gh_cli):
    """Uses fixtures from different modules transparently."""
    # Test code using fixtures from database.py and mocks.py
```

### Current Status (Task #1656 Complete)

- `fixtures/__init__.py`: Contains pytest_plugins list with all 6 fixture modules loaded
- `conftest.py`: Reduced from 758 to 149 lines (80% reduction); core autouse fixtures remain
- **Completed extractions**:
  - `fixtures/database.py`: Database fixtures (db_path, repo, db_with_epic_and_tasks) - Task #1652
  - `fixtures/mocks.py`: Mock fixtures (mock_gh_cli, mock_subprocess, etc.) - Task #1653
  - `fixtures/accumulated_context.py`: V1/V2 context, corrupt files - Task #1654
  - `fixtures/worktree.py`: Session directory, worktree root - Task #1655
  - `fixtures/connection_tracking.py`: Connection leak detection - Task #1656
  - `fixtures/pre_compact.py`: Pre-compact worker test fixtures - Task #1656
  - `fixtures/helpers.py`: Utility functions (not fixtures, imported directly) - Task #1656

### Backward Compatibility Pattern

`conftest.py` maintains backward compatibility by re-exporting helper functions:

```python
# Backward Compatibility Re-exports
from tests.fixtures.helpers import (
    assert_no_connection_leaks,
    assert_task_state,
    generate_sql_injection_payloads,
    make_valid_review,
    make_valid_review_findings,
    run_concurrent_operations,
)
```

Tests can import from either location without breaking.

## Testing Patterns

### MUST Mock External Services

```python
def test_subprocess_calls(mock_gh_cli, db_path):
    """Always mock subprocess calls - never call real external commands."""
    mock_gh_cli.return_value.returncode = 0
    # Test code...
```

### Database Tests Use In-Memory

```python
def test_epic_operations(db_path):
    """db_path fixture provides isolated in-memory database."""
    conn = sqlite3.connect(db_path)
    # All operations isolated to this test
```

### Use tmp_path for Files

```python
def test_file_operations(tmp_path):
    """Never write to real file system."""
    test_file = tmp_path / "test.md"
    test_file.write_text("content")
```

### Check Connection Leaks

```python
def test_no_connection_leak(db_path, repo, connection_tracker):
    """Verify connections are properly closed."""
    # Use repo fixture (see tests/fixtures/database.py)
    repo.create_epic("test", "desc")
    assert connection_tracker.open_connections == 0
```

### Import Modules for Monkeypatching (Critical)

When patching functions with `monkeypatch.setattr()`, import the **module reference**, not the function directly. Python binds names at import time, so direct function imports won't see patches applied to the module.

```python
# ✅ CORRECT: Import module, use module.function()
from formaltask import accumulated_context as ac

def test_load_context(tmp_path, monkeypatch):
    # Patch works because we call ac.load_accumulated_context()
    monkeypatch.setattr(ac, "load_accumulated_context", mock_fn)
    result = ac.load_accumulated_context(tmp_path / "ctx.json")

# ❌ WRONG: Direct import bypasses patches
from formaltask.accumulated_context import load_accumulated_context

def test_load_context(tmp_path, monkeypatch):
    # Patch has no effect! Direct import already bound the original function
    monkeypatch.setattr(ac, "load_accumulated_context", mock_fn)
    result = load_accumulated_context(tmp_path / "ctx.json")  # Calls original!
```

**Classes can be imported directly** since they're instantiated with test data, not patched:

```python
# Import module reference for patchable functions
from formaltask import accumulated_context as ac

# Import classes directly (instantiated, not patched)
from formaltask.accumulated_context import (
    AccumulatedContext,
    PersistentDecision,
)
```

**Why this matters:** The `conftest.py` autouse fixture `bypass_accumulated_context_path_validation` patches `ac_module` functions. Tests must use `ac.function_name()` pattern for patches to apply.

## Test Naming Conventions

```
test_{module}_{function}_{scenario}.py

Examples:
- test_epic_repository_create_epic.py
- test_issue_complete_with_review.py
- test_task_guards_evidence_required.py
```

## Coverage Requirements

- Target: **>80%** for `formaltask/`
- TDD Guard enforces coverage on commit
- View coverage: `pytest --cov=formaltask --cov-report=html`

## BATS Testing (Bash)

For bash hook scripts:

```bash
# File: test_hook.bats
@test "hook succeeds with valid input" {
    run ./my-hook.sh valid-input
    [ "$status" -eq 0 ]
}

@test "hook fails with invalid input" {
    run ./my-hook.sh invalid
    [ "$status" -eq 1 ]
    [[ "$output" == *"Error:"* ]]
}
```

Run:
```bash
bats tests/test_hook.bats
```

## Property-Based Testing

Use Hypothesis for property tests:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1))
def test_epic_name_validation(name):
    """Property: any non-empty string is valid epic name."""
    # Test property...
```

Location: `tests/property/`

## Common Test Patterns

### Testing CLI Commands

```python
def test_task_complete_command(db_with_epic_and_tasks, mock_gh_cli):
    from formaltask.cli.commands.task_complete import execute
    result = execute(["3"])  # Task ID
    assert result == 0
```

### Testing Repository Operations

```python
def test_epic_create(db_path, repo):
    # Use repo fixture (see tests/fixtures/database.py)
    repo.create_epic("test-epic", "description")
    epic = repo.get_epic("test-epic")
    assert epic is not None
    assert epic["name"] == "test-epic"
```

### Testing Validators

```python
def test_validator_blocks_invalid(monkeypatch, tmp_path):
    """Validator should block invalid tool calls."""
    # Setup mock input
    # Call validator
    # Assert blocked
```

### End-to-End Integration Testing

For testing complex workflows that span multiple components, use these patterns:

#### tmux Worker Integration Tests

When testing components that interact with tmux workers and state files:

```python
def test_worker_state_workflow(tmp_path, monkeypatch):
    """Test complete workflow: worker → hook → state file."""
    # Mock tmux environment
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create state directory structure
    state_dir = tmp_path / ".cache" / "tmux-claude-status"
    state_dir.mkdir(parents=True)

    # Mock subprocess for tmux commands
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "task-42"

    with patch("subprocess.run", return_value=mock_result):
        # Test workflow steps
        pass
```

#### Git Integration Tests

For testing git utilities with real git repositories (Task #1831):

```python
def test_git_function_with_real_repo(tmp_path):
    """Test git_utils functions with actual git repository."""
    from formaltask.utils.git_utils import get_head_sha, commit_exists, is_ancestor

    # Create temporary git repository
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, capture_output=True, check=True
    )

    # Test with real repo
    sha = get_head_sha(tmp_path)
    assert sha is not None
    assert len(sha) == 40
    assert commit_exists(sha, tmp_path) is True
```

**Key patterns:**
- Use `tmp_path` fixture for temporary git repositories
- Configure git user/email to avoid errors
- Use `--allow-empty` commits for minimal test setup
- Test both success and error cases (in/outside git repo)
- Verify actual git operations vs mocked behavior

#### Multi-Component State Testing

Test state file operations across components:

```python
def test_state_file_workflow(tmp_path, monkeypatch):
    """Test state file writes and reads across multiple components."""
    from formaltask.stop_handoff_enforcer import main as stop_handoff
    from formaltask.worker_health_analyzer import read_worker_state

    # Setup state directory
    state_dir = tmp_path / ".cache" / "tmux-claude-status"
    state_dir.mkdir(parents=True)

    # Step 1: Component A writes state
    # Step 2: Component B reads state via read_worker_state()
    # Step 3: Assert expected state transformations
```

#### Transcript File Testing

For hooks that parse transcript files:

```python
def test_transcript_parsing_workflow(tmp_path):
    """Test transcript parsing with handoff packets."""
    # Create transcript with handoff data
    transcript_file = tmp_path / "transcript.jsonl"
    handoff_json = json.dumps({"phase": "ready_for_review"})
    transcript_content = [
        {"type": "assistant", "message": {
            "content": f"Done!\n@@@HANDOFF\n{handoff_json}\n@@@HANDOFF"
        }},
    ]
    transcript_file.write_text(
        "\n".join(json.dumps(t) for t in transcript_content)
    )

    # Test transcript parsing logic
```

#### Integration Test Structure

Organize complex integration tests by workflow phase:

```python
class TestEndToEndWorkflow:
    """Complete workflow integration tests."""

    def test_phase_1_setup(self):
        """Test initial component setup."""

    def test_phase_2_processing(self):
        """Test middle workflow steps."""

    def test_phase_3_completion(self):
        """Test final workflow steps."""

    def test_complete_integration(self):
        """Test entire workflow end-to-end."""
```

## Debugging Failed Tests

```bash
# Run with verbose output
pytest tests/unit/test_failing.py -v -s

# Run with debugger
pytest tests/unit/test_failing.py --pdb

# Run single test with print statements
pytest tests/unit/test_failing.py::test_name -v -s
```

## Anti-Patterns

- Never call real APIs (GitHub, OpenAI, MCP)
- Never use real file paths (use tmp_path)
- Never skip mocking subprocess calls
- Never leave database connections open
- Never use time.sleep() in tests (use mocks)
- Never import functions directly when monkeypatching (use module reference)
- Never use `inspect.getsource()` to verify function calls (use behavioral testing with mocks)
  - **Exception**: AST parsing is acceptable for TDD contract tests that verify safety patterns (Task #1904)

### Behavioral Testing vs Source Inspection (Task #1297)

Generally prefer behavioral testing with mocks over source inspection. However, AST parsing has specific valid uses.

#### Standard Pattern: Behavioral Testing

Use behavioral testing to verify function calls and control flow:

```python
# ❌ WRONG: Source code inspection (brittle, anti-pattern)
def test_main_calls_function():
    source = inspect.getsource(main)
    assert "try_generate_from_accumulated_context" in source

# ✅ CORRECT: Behavioral testing (verifies actual runtime behavior)
def test_main_uses_accumulated_context_when_available(mocker, tmp_path):
    """Test that when accumulated context returns narrative, transcript is NOT parsed."""
    mock_narrative = MagicMock()
    mock_narrative.narrative = "Test narrative from accumulated context"

    # Mock the function to return a narrative
    mocker.patch(
        "module.try_generate_from_accumulated_context",
        return_value=mock_narrative
    )

    # Mock the fallback function to track if it's called
    mock_fallback = mocker.patch("module.fallback_function")

    # Act: Call the function under test
    result = function_under_test(test_input)

    # Assert: Verify actual behavior
    mock_fallback.assert_not_called()  # Fallback should NOT be called
    assert result["narrative_obj"] == mock_narrative
    assert "Test narrative" in result["summary"]
```

**Why behavioral testing is better:**
- Tests actual runtime behavior, not implementation details
- Fails when early-return logic is removed (catches regressions)
- Verifies complete return dict structure
- Mock assertions prove control flow paths taken
- More maintainable when code structure changes

**Pattern from Task #1297:** Mock the primary path to return a value, mock the fallback path to track calls, then assert the fallback was NOT called when primary path succeeds.

**Pattern from Task #1299:** Test validation dict structure by mocking the data source, calling the function, and asserting all required fields are present with correct values.

```python
# ✅ CORRECT: Validation dict structure testing (Task #1299)
def test_builds_validation_dict_from_accumulated_context(mocker, tmp_path):
    """Test validation dict structure when using accumulated context."""
    # Create mock data with specific characteristics for testing
    long_narrative = "A" * 250  # Long enough to test truncation
    mock_narrative = MagicMock()
    mock_narrative.narrative = long_narrative

    # Mock the data source
    mocker.patch(
        "session_end_worker.try_generate_from_accumulated_context",
        return_value=mock_narrative
    )

    # Act: Call function that builds validation dict
    result = generate_validation_result(hook_data, session_id, session_data)

    # Assert: All required fields present with correct structure
    assert "summary" in result
    assert "completeness" in result
    assert "missing_items" in result
    assert "topic_accurate" in result
    assert "narrative_obj" in result
    assert "session_id" in result

    # Assert: Field values are correct for this path
    assert result["summary"] == long_narrative[:200] + "..."
    assert result["completeness"] == "complete"
    assert result["missing_items"] == []
    assert result["narrative_obj"] is mock_narrative
```

#### Exception: AST Parsing for TDD Contract Tests (Task #1904)

AST parsing is acceptable for TDD contract tests that verify safety patterns where behavioral testing would be impractical:

```python
# ✅ ACCEPTABLE: AST parsing for safety pattern verification
def test_refresh_timeout_30_seconds(self):
    """_refresh_epic_lists should use asyncio.wait_for with timeout=30.0.

    Uses AST parsing for robustness against formatting changes (P2 review fix).
    """
    import ast
    import textwrap
    import inspect

    from formaltask.cli.commands.pm_browse.app import EpicNavigator

    method = EpicNavigator._refresh_epic_lists
    original = getattr(method, "__wrapped__", method)
    source = textwrap.dedent(inspect.getsource(original))
    tree = ast.parse(source)

    # Look for wait_for call with timeout keyword argument
    has_wait_for = False
    has_timeout_30 = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            func_name = None
            if isinstance(func, ast.Attribute):
                func_name = func.attr
            elif isinstance(func, ast.Name):
                func_name = func.id

            if func_name == "wait_for":
                has_wait_for = True
                for keyword in node.keywords:
                    if keyword.arg == "timeout":
                        if isinstance(keyword.value, ast.Constant):
                            if keyword.value.value in (30, 30.0):
                                has_timeout_30 = True

    assert has_wait_for, "Should use asyncio.wait_for"
    assert has_timeout_30, "Should have 30 second timeout"
```

**When AST parsing is appropriate:**
- TDD contract tests that verify specific safety patterns (timeouts, error handling)
- Tests where behavioral testing would require complex async mocking of framework internals
- Verifying implementation patterns that are safety requirements, not just behavior

**Key patterns:**
- Use `textwrap.dedent()` to handle indentation properly
- Parse with `ast.parse()` instead of string matching for formatting robustness
- Focus on safety-critical patterns, not general function calls
- Include clear justification in test docstring

**Still prefer behavioral testing when:**
- Testing control flow and return values
- Verifying function calls and interactions
- Testing business logic and data transformations

## Common Gotchas

### PROJECT_ROOT Environment Variable (Import-Order Dependency)

The `conftest.py` sets `PROJECT_ROOT` environment variable **before** any hooks modules are imported:

```python
# In conftest.py (lines 34-37)
os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))
```

**Why this matters:** Some hooks modules (e.g., `epic_decompose.py`) read `PROJECT_ROOT` at module load time. Without this early setup, tests in git worktrees would get incorrect paths.

**Implications:**
- `conftest.py` MUST be loaded before any hooks module imports
- Running individual test files directly may fail if pytest doesn't load conftest.py first
- Always run tests via `pytest` command (not direct Python execution)

**If tests fail with path-related errors:**
1. Ensure you're running via `pytest`, not `python test_file.py`
2. Check that `conftest.py` is in the test discovery path
3. Verify `PROJECT_ROOT` is set correctly for your worktree
