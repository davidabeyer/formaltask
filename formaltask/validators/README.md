# Validators

PreToolUse validation framework for Claude Code hooks. Enforces security policies, TDD discipline, and workflow guardrails.

## Quick Start

```python
from formaltask.validators.stub_detector import detect_stubs

# Check code for stub patterns
violations = detect_stubs(code_content, file_path="example.py")
for v in violations:
    print(f"Line {v.line}: {v.pattern} - {v.code}")
```

## Architecture

Validators integrate through a two-tier system:

```
hooks/pretool/runner.py          # Entry point, reads JSON from stdin
       │
       ▼
hooks/pretool/phases/*.py        # Thin wrappers (17 phases)
       │
       ▼
formaltask/validators/*.py       # Validation logic (25+ validators)
       │
       ▼
JSON response to stdout          # {decision: allow|block, reason?, additionalContext?}
```

**Key insight:** Most phases are thin wrappers that delegate to `formaltask/validators/`. Edit validators, not phases. Exceptions: `stub_detector` and `tdd_guard` phases contain implementation logic.

## Validator Interface

All validators follow this contract:

```python
def check(ctx: dict) -> dict | None:
    """
    Args:
        ctx: Hook context with tool_name, tool_input, etc.

    Returns:
        None           - Allow (pass to next phase)
        {"decision": "block", "reason": str}  - Block with message
        {"decision": "allow", "additionalContext": str}  - Allow with advisory
    """
```

### Context Structure

```python
ctx = {
    "tool_name": "Write",           # Tool being invoked
    "tool_input": {                 # Tool-specific parameters
        "file_path": "/path/to/file.py",
        "content": "..."
    },
    "session_id": "abc123",         # Current session
    "cwd": "/Users/x/project"       # Working directory
}
```

## Validator Categories

### Security (Fail-Closed)

Block on ANY error. Never allow on exception.

| Validator | Purpose |
|-----------|---------|
| `db_guard` | Validates FormalTask database paths |
| `sql_guard` | Blocks write SQL to formaltask.db |
| `bash_file_guard` | Prevents TDD bypass via shell |
| `planning_schema_validator` | Validates CriterionV2 in planning YAML files |

### Workflow (Fail-Open)

Allow on error to not block work.

| Validator | Purpose |
|-----------|---------|
| `stub_detector` | Detects placeholder implementations |
| `tdd_guard` | Enforces test-first development |
| `doc_guard` | Pre-commit documentation checks |

### Redirection (Advisory)

Suggest better tools, don't block.

| Validator | Purpose |
|-----------|---------|
| `tool_redirect` | Blocks WebSearch, suggests exa via rules kernel |
| `grep_to_warpgrep` | Suggests warpgrep for semantic search |

## Adding a New Validator

### Step 1: Create Validator File

```python
# formaltask/validators/my_validator.py
"""PreToolUse Hook: Brief description."""

import json
import sys

TOOL_MATCH = ["Write", "Edit"]  # Tools this applies to


def check(ctx: dict) -> dict | None:
    """Main validation logic."""
    tool_name = ctx.get("tool_name", "")

    # Guard: Only check matching tools
    if tool_name not in TOOL_MATCH:
        return None

    tool_input = ctx.get("tool_input", {})

    # Your validation logic here
    if should_block(tool_input):
        return {
            "decision": "block",
            "reason": "Blocked because..."
        }

    return None  # Allow


def main():
    """CLI entry point for standalone testing."""
    try:
        ctx = json.load(sys.stdin)
        result = check(ctx)
        if result and result.get("decision") == "block":
            print(json.dumps(result))
            sys.exit(2)  # Exit 2 = block
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)
    except Exception as e:
        # Fail-open for non-security validators
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### Step 2: Create Phase Wrapper

```python
# hooks/pretool/phases/my_validator.py
"""Phase wrapper for my_validator."""

from formaltask.validators.my_validator import check as _check


def check(ctx: dict) -> dict | None:
    return _check(ctx)
```

### Step 3: Register in Runner

```python
# hooks/pretool/runner.py
from hooks.pretool.phases import my_validator

PHASES = [
    # ... existing phases ...
    my_validator.check,
]
```

### Step 4: Add Tests

```python
# tests/test_my_validator.py
import pytest
from formaltask.validators.my_validator import check


def test_allows_valid_input():
    ctx = {"tool_name": "Write", "tool_input": {"file_path": "ok.py"}}
    assert check(ctx) is None


def test_blocks_invalid_input():
    ctx = {"tool_name": "Write", "tool_input": {"file_path": "bad.py"}}
    result = check(ctx)
    assert result["decision"] == "block"
```

## Execution Flow

### Phase Order

First block wins. Phases execute in order:

1. `skill_stage_tracker` - Skill execution stage tracking
2. `task_context_injector` - Task context injection
3. `doc_guard` - Pre-commit documentation checks
4. `sql_guard` - Database write protection
5. `tdd_guard` - Test-first enforcement
6. `task_validator` - Task ID validation
7. `todowrite_validator` - Workflow state tracking
8. `skill_todo_validator` - Skill todo state validation
9. `git_safety` - Force flags, no-verify blocking
10. `bash_file_guard` - Shell command validation
11. `tool_redirect` - Tool redirection via rules kernel (advisory)
12. `grep_redirect` - Tool redirection (advisory)
13. `formaltask_db_guard` - Database path validation
14. `webfetch_redirect` - URL transformation (advisory)
15. `feature_branch_guard` - Branch targeting
16. `prompt_injection` - Prompt injection detection
17. `epic_decompose_validator` - Epic decomposition validation
18. `planning_schema_validator` - CriterionV2 validation in planning YAML

### Error Handling

```python
# In runner.py
for fn in PHASES:
    try:
        result = fn(ctx)
        if result and result.get("decision") == "block":
            return result  # First block wins
    except Exception:
        continue  # Fail-open: skip broken phase
```

## Key Files

| File | Purpose |
|------|---------|
| `stub_detector.py` | AST-based stub detection (5 patterns) |
| `db_guard.py` | Database path security |
| `sql_guard.py` | SQL write blocking |
| `tdd_guard.py` | TDD enforcement transformer |
| `doc_detection.py` | File-to-doc mapping |
| `gate_enforcer.py` | Task completion gates |
| `planning_schema_validator.py` | CriterionV2 validation in planning YAML |

## Testing Validators

### Unit Testing

```python
# Direct function call
from formaltask.validators.stub_detector import detect_stubs

code = "def foo(): pass"
violations = detect_stubs(code, "test.py")
assert len(violations) == 1
```

### Integration Testing

```bash
# CLI invocation
echo '{"tool_name": "Write", "tool_input": {"file_path": "x.py"}}' | \
  python -m formaltask.validators.db_guard
```

### Clear Config Cache

```python
# In tests, clear cached config
from formaltask.validators.doc_guard_config import clear_config_cache
clear_config_cache()
```

## See Also

- `hooks/pretool/runner.py` - Phase orchestration
- `hooks/pretool/phases/` - Phase wrappers
- `tests/` - Test coverage (19 files)
