---
consumes: [audit-status]
produces: [target-file]
---
## Phase 2: Present Target

**quick:** Skip AskUserQuestion. Use target from user or largest file in current module.

**full:** Use AskUserQuestion:
- **Next by LOC** (Recommended) - Largest unaudited file
- **Pick from list** - Top 5 candidates
- **Specific file** - Jump to path
- **Focus areas** - Optional: Naming, Typing, Pythonic, Documentation

**EXIT CRITERIA:** Have target (1 file or 3-5 related files max)
