---
consumes: []
produces: [audit-target]
---

## Mode Selection

| Trigger | Action |
|---------|--------|
| Default | Single file mode. Skip AskUserQuestion |
| User requests scope | Ask: Single file / Module batch (Recommended) / Custom |

**Module batch:** Read `skills/_references/orchestration.md`, spawn parallel workers.

## Load Status + Select Target

**quick:** Ask user for target file or use largest in current module.

**full:**
```bash
python3 ~/.claude/skills/_audit_tracker/parse_status.py ANTIREZ
```

Present options: Next by LOC (Recommended) / Show more / Pick from list / Specific file
