---
consumes: [user-request]
produces: [audit-status]
---
## Phase 1: Load Status

**quick:** Skip status script. Ask user for target file or use argument.

**full:**
```bash
python3 ~/.claude/skills/_audit_tracker/parse_status.py STYLE
```

Outputs: progress, next 5 targets by LOC, module breakdown.
