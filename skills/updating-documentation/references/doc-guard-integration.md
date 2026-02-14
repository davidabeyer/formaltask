# Doc-Guard Integration

## Workflow

1. **Hook detects changes** to documented areas (hooks/lib/*.py, etc.)
2. **Generates suggestions** in pending.json
3. **This skill guides updates** based on suggestions
4. **User clears suggestions** after addressing

## Pending.json Structure

```json
{
  "entries": [
    {
      "summary": "Brief description of change",
      "suggestions": [
        {
          "file": "README.md",
          "section": "Key Patterns",
          "reason": "New pattern added",
          "suggested_content": "Content to add"
        }
      ]
    }
  ]
}
```

## CLI Commands

```bash
# Check pending suggestions
./hooks/cli/doc_guard_cli.py pending

# Clear suggestions after addressing
./hooks/cli/doc_guard_cli.py clear
```

## File Locations

- **Doc-guard CLI**: `hooks/cli/doc_guard_cli.py`
- **Pending suggestions**: `.claude/doc-guard/pending.json`
- **Main documentation**: `README.md`
- **Hook documentation**: `hooks/README.md`
