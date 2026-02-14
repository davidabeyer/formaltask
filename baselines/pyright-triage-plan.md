# Pyright Type Error Triage Plan

**Baseline Date:** 2025-12-18 (updated)
**Total Errors:** 527 (baseline with reportUnusedImport disabled)
**Warnings:** 0

> **Note:** For up-to-date error counts, see `baselines/pyright-baseline.txt` which is regenerated with each baseline update.

## Error Categories (Priority Order)

### P0 - Critical (Potential Runtime Bugs)

| Category | Count | Action |
|----------|-------|--------|
| reportUndefinedVariable | 1 | Fix immediately - actual undefined names |
| reportReturnType | 6 | Fix - function returns don't match declared types |
| reportGeneralTypeIssues | 2 | Investigate - may indicate logic errors |

### P1 - High (Type Safety)

| Category | Count | Action |
|----------|-------|--------|
| reportArgumentType | 169 | Add type annotations or casts |
| reportOptionalMemberAccess | 21 | Add null checks before access |
| reportOptionalSubscript | 6 | Add null checks before subscript |
| reportOptionalCall | 1 | Add null check before call |
| reportPossiblyUnboundVariable | 16 | Initialize variables or restructure |

### P2 - Medium (Code Quality)

| Category | Count | Action |
|----------|-------|--------|
| reportAttributeAccessIssue | 86 | Add type hints or use Protocol |
| reportOperatorIssue | 9 | Add type hints for operators |
| reportCallIssue | 7 | Fix function signatures |
| reportFunctionMemberAccess | 5 | Add type hints |
| reportInvalidStringEscapeSequence | 8 | Use raw strings r"..." |

### P3 - Low (Cleanup)

| Category | Count | Action |
|----------|-------|--------|
| reportUnusedImport | 124 | STALE - disabled in favor of Ruff F401 |
| reportUnusedVariable | 65 | Remove or prefix with _ |
| reportUnusedExpression | 1 | Remove or use result |

## Recommended Fix Order

1. **Immediate:** Fix 1 undefined variable (actual bug)
2. **This Sprint:** Fix P0 and P1 errors in public APIs
3. **Gradual:** Address P2/P3 via `# type: ignore[error-code]` or fixes
4. **CI Enforcement:** Fail on new errors only (baseline comparison)

## Files with Most Errors (Top 10)

Run to identify from JSON baseline:
```bash
jq -r '.files | to_entries | map({file: .key, count: .value | length}) | sort_by(-.count) | .[0:10] | .[] | "\(.count)\t\(.file)"' baselines/pyright-baseline.json
```

## Escape Hatches

- Single error: `# type: ignore[reportArgumentType]`
- Entire file: Add to pyproject.toml `exclude` list
- All of type: Set `reportXxx = "none"` in pyproject.toml

## CI Integration Notes

- Pre-commit hook runs basedpyright on all Python files (with exclude patterns in pyproject.toml)
- CI workflow (`.github/workflows/pre-commit.yml`) includes `setup-node@v4` for basedpyright
- Baseline comparison ensures no NEW errors are introduced
