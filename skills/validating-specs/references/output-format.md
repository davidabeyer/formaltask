# Spec Validator Output Format

Structured output for validation findings.

## Finding Structure

```json
{
  "task_id": 42,
  "task_title": "Add auth validation",
  "findings": [
    {
      "severity": "P0",
      "category": "file_missing",
      "claim": "Modify hooks/lib/auth_handler.py:45-67",
      "evidence": "File does not exist. Glob('hooks/lib/auth*.py') returned 0 results",
      "suggestion": "Verify correct file path. Found similar: hooks/lib/authentication.py"
    }
  ]
}
```

## Summary Format

```markdown
## Spec Validation Results

**Epic:** {epic-name}
**Tasks Validated:** {count}
**Findings:** {P0 count} P0, {P1 count} P1, {P2 count} P2

### P0 - Critical (Blocks Implementation)

#### Task #{id}: {title}
- **{CATEGORY}**: {claim}
  - **Evidence**: {evidence from tool}
  - **Fix**: {suggestion}

### P1 - High (Fix Before Implementation)
...

### P2 - Medium (Advisory)
...
```

## Severity Categories

| Category | Description |
|----------|-------------|
| `file_missing` | Referenced file does not exist |
| `line_range_invalid` | File exists but line numbers out of range |
| `symbol_missing` | Function/class not found in codebase |
| `symbol_moved` | Symbol exists in different location |
| `signature_mismatch` | Function signature differs from claim |
| `library_feature_missing` | Library feature doesn't exist |
| `api_mismatch` | API differs from assumption |
| `pattern_violation` | Implementation contradicts referenced pattern |
