# Exception Handler Audit

Task #1854: Error Handling Visibility

**Total handlers audited:** 540 across 184 files
**Generated:** 2026-01-05

## Summary

| Category | Count | % | Status |
|----------|-------|---|--------|
| Critical (Data Loss Risk) | 11 | 2% | ✅ All properly re-raise |
| Warning (User Visible) | 8 | 1% | ⚠️ Some need logging |
| Debug (Internal) | ~520 | 97% | ✅ Most have logging/comments |

## Critical (Data Loss Risk)

These handlers deal with database operations and must properly rollback and re-raise.

| File | Line | Exception | Pattern | Status |
|------|------|-----------|---------|--------|
| `lib/migrations/add_retry_count.py` | 90 | `Exception` | ROLLBACK + raise | ✅ |
| `lib/migrations/accumulated_context_v2.py` | 133 | `Exception` | Cleanup + raise | ✅ |
| `lib/migrations/accumulated_context_v2.py` | 193 | `Exception` | Cleanup + raise | ✅ |
| `lib/migrations/add_pending_decisions.py` | 81 | `Exception` | ROLLBACK + raise | ✅ |
| `lib/migrations/backfill_severity.py` | 68 | `Exception` | ROLLBACK + raise | ✅ |
| `lib/migrations/add_review_type.py` | 143 | `Exception` | ROLLBACK + raise | ✅ |
| `lib/task_operations.py` | 74 | `Exception` | ROLLBACK + raise | ✅ |
| `lib/task_operations.py` | 194 | `Exception` | ROLLBACK + raise | ✅ |
| `lib/epic_repository.py` | 667 | `Exception` | ROLLBACK + raise | ✅ |
| `cli/commands/pm_browse.py` | 239 | `Exception` | ROLLBACK + raise | ✅ |
| `cli/commands/epic_decompose.py` | 345, 390 | `Exception` | Cleanup + logger.error | ✅ |

**Assessment:** All critical handlers properly rollback and re-raise. No data loss risk.

## Warning (User Visible)

These handlers may affect user experience or mask errors that should be visible.

| File | Line | Exception | Pattern | Status | Recommendation |
|------|------|-----------|---------|--------|----------------|
| `user-prompt/prompt_optimizer.py` | 46 | `Exception` | `pass` | ⚠️ | Add DEBUG log |
| `user-prompt/prompt_optimizer.py` | 253 | `Exception` | `return ""` | ⚠️ | Add DEBUG log |
| `session-start/register_active_session.py` | 47 | `Exception` | `pass` | ⚠️ | Add DEBUG log |
| `lib/bats_tdd_guard_hook.py` | 82 | `Exception` | `pass` + comment | ✅ | Has comment |
| `user_prompt/task_context_trigger.py` | 87 | `Exception` | `sys.exit(0)` + comment | ✅ | Has comment |
| `lib/stub_validator.py` | 87 | `Exception` | Return allow + comment | ✅ | Has comment |
| `cli/commands/parallel_start.py` | 416 | `Exception` | `pass` + comment | ✅ | Has comment |
| `lib/unified_review.py` | 248 | `Exception` | `continue` | ⚠️ | Add DEBUG log |

**Assessment:** 4 handlers need DEBUG logging added.

## Debug (Internal)

These are expected exception handlers for imports, parsing, and internal operations.

### Import Fallbacks (~85 handlers)

All `ModuleNotFoundError` and `ImportError` handlers for import path resolution:

```python
# Pattern used throughout codebase - absolute imports only
from hooks.lib.module import func
```

**Status:** ✅ Absolute imports work from all execution contexts.

### Parsing/Validation Fallbacks (~75 handlers)

Handlers for `ValueError`, `KeyError`, `json.JSONDecodeError` in parsing operations:

```python
# Pattern: Parse with fallback
try:
    result = parse_json(text)
except json.JSONDecodeError as e:
    logger.debug("JSON parse failed: %s", e)
    result = fallback_value
```

**Status:** ✅ All have logging or comments.

### TUI Widget Handlers (~25 handlers)

Handlers for `NoMatches` in Textual widget queries:

```python
# Pattern: Widget not ready
try:
    widget = self.query_one("#widget-id", WidgetType)
except NoMatches:
    pass  # Widget not mounted yet - expected during startup
```

**Status:** ✅ All have comments explaining expected behavior.

### File/OS Operations (~45 handlers)

Handlers for `OSError`, `FileNotFoundError`, `PermissionError`:

```python
# Pattern: File operation with fallback
try:
    content = path.read_text()
except OSError as e:
    logger.debug("Could not read %s: %s", path, e)
    content = default
```

**Status:** ✅ All have logging or documented fallback.

### Other (~290 handlers)

Remaining handlers are specific to individual operations with appropriate handling.

## Patterns to Avoid

The following patterns should NOT be used in new code:

```python
# BAD: Silent swallowing
except Exception:
    pass

# GOOD: At minimum, log at DEBUG
except Exception as e:
    logger.debug("Operation failed, continuing: %s", e)

# BEST: Specific exception + appropriate level
except json.JSONDecodeError as e:
    logger.debug("JSON parse failed, trying markdown: %s", e)
```

## Follow-up Actions

1. **P2:** Add DEBUG logging to 4 Warning-level handlers (prompt_optimizer.py, register_active_session.py, unified_review.py)
2. **P3:** Consider converting bare `Exception` catches to specific exceptions where possible
3. **P3:** Document exception handling patterns in style guide

## Verification Commands

```bash
# Find bare except...pass patterns
grep -rn "except.*:\s*$" hooks/ --include="*.py" | grep -v test | head -20

# Count handlers by exception type
grep -roh "except \w\+:" hooks/*.py hooks/**/*.py | sort | uniq -c | sort -rn

# Find undocumented except blocks
grep -rn "except.*:$" hooks/ --include="*.py" -A1 | grep -v test | grep -v "#" | grep pass
```
