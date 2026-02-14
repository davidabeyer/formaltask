---
consumes: [user-request]
produces: [hunt-target, hunt-focus]
---

# Phase -2: Show Run History

Display `SkillRun.format_history("hunting-dead-code", limit=10)` so user can resume or reference previous hunts.

# Phase -1: Clarification (full only)

**quick:** Skip clarification. Target = all source, Focus = all categories.

Ask via AskUserQuestion:
1. **Target** - All source / Specific directory / Recent changes
2. **Focus** - Unused imports / Orphan functions / Unreachable code / Obsolete features (multiSelect)

Record answers to `~/projects/audits/hunting-dead-code/{date}-{target}.md`
