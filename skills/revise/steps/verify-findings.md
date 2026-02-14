---
consumes: [applied-fixes]
produces: [verified-findings]
---
# Phase 2: Verify Before Fixing

**ABSOLUTELY MANDATORY -- NO EXCEPTIONS.**

Even if:
- User expresses frustration -> Still verify
- Context seems obvious -> Still verify
- Time pressure implied -> Still verify

If you skip this phase, you WILL produce wrong output. The skill's value comes from verification, not speed.

**Grep codebase BEFORE applying ANY fix.**

For EACH finding that references a function/file/line:
1. Grep for the referenced symbol in actual codebase
2. Mark as: **VALID** (real issue) | **INVALID** (critique wrong) | **STALE** (already fixed/deleted)
3. Only fix VALID items. Document INVALID/STALE with evidence.

**New findings:** If verification reveals issues the critique missed (e.g., grep shows 39 refs but critique only mentions 10), record the expanded scope. Fix the real problem, not just the critique's partial description.

**EXIT CRITERIA:** Each finding marked VALID/INVALID/STALE with grep evidence. New findings recorded.
