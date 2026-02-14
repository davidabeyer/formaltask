---
name: task
description: Single task creation shortcut. Use when /plan routes here (scope=TASK)
  or for quick task capture. For 2+ tasks, use /plan instead.
argument-hint: <title or description>
inherit:
- review
tools:
- auggie
required_todos:
- quick-discovery
- validate-paths
- validate-epic
- specify
- write-artifact
---

<role>
WHO: Quick task creator
ATTITUDE: A task with hallucinated paths wastes an entire work session. Unacceptable.
</role>

<purpose>
Your job is to create one task artifact with verified paths and testable criteria. No planning overhead.
</purpose>

<workflow>

## Phase 0: Quick Discovery

```python
mcp__auggie-mcp__codebase-retrieval(
    information_request=f"Find code related to: {description}"
)
```

If 0 paths found → search broader. If 5+ files involved → "Scope too big. Run: `/plan {description}`" **STOP**

**EXIT CRITERIA:** 1-4 file paths with line numbers.

---

## Phase 1: Validate Paths

Spawn plan-explorer to verify:
```python
Task(subagent_type="plan-explorer",
     prompt=f"Validate these paths exist and contain expected code: {paths}")
```

**ABSOLUTE PATHS ONLY** in prompts. No `~/` or relative paths. Hooks enforce this.

**EXIT CRITERIA:** Paths confirmed valid. Invalid → re-run Phase 0.

---

## Phase 2: Validate Epic

```bash
ft epic list --names | grep -qx "$EPIC_NAME"
```

**No epic specified?** Default to inbox with confirmation:
```python
AskUserQuestion(questions=[{
    "question": "Add this task to inbox epic?",
    "header": "Epic",
    "options": [
        {"label": "Yes, inbox", "description": "Quick capture, triage later"},
        {"label": "No, different epic", "description": "I'll specify which epic"}
    ],
    "multiSelect": False
}])
```

**EXIT CRITERIA:** Epic validated or defaulted to inbox.

---

## Phase 3: Specify

**Title:** Action verb + specific scope.
- Bad: "Update tests" → Good: "Add pytest fixtures for auth mocking"

**REJECT these vague patterns:**
```
properly, correctly, well, good, clean, improved, better,
appropriate, suitable, handles errors, is robust, is efficient,
works correctly, handles edge cases, is maintainable, follows best practices
```

Every criterion MUST be binary testable. Can't write a test? Rewrite it.

**Reviews:** Default `code-quality`. Add based on domain:

| Task Content | Add Review |
|--------------|-----------|
| Auth, credentials, user input | `security` |
| Database operations | `sqlite` |
| Loops, large data | `perf` |
| File paths | `path-security` |
| State transitions | `state-machine` |

**Documentation required:** `true` only for public API, CLI, user-facing changes.

**EXIT CRITERIA:** Title + 2-3 testable criteria + reviews + doc flag.

---

## Phase 4: Write Artifact

```python
from pathlib import Path
from datetime import datetime, timezone
import re

date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

artifact_dir = Path.home() / "projects" / "one-offs" / f"{date}-{slug}"
artifact_dir.mkdir(parents=True, exist_ok=True)
```

```markdown
# Task: {title}

**Epic:** {epic_name}
**Required reviews:** {reviews}
**Documentation required:** {true|false}

## Goal
{One sentence}

## Acceptance Criteria
- [ ] {criterion_1}
- [ ] {criterion_2}
- [ ] No new classes unless unavoidable (plain functions preferred)
- [ ] Junior dev understands each function in 30 seconds

## Anti-patterns (DO NOT)
- No wrapper functions that just call another function
- No config options added "for flexibility"
- No "Manager" or "Handler" classes

## Files to Modify
- `{file}:{line}` - {change}
```

**Output:**
```
══════════════════════════════════════════════════════════════
   ✓ TASK: {title}
══════════════════════════════════════════════════════════════
Artifact: {artifact_dir}/task.md

Next: /critique {artifact_dir}
══════════════════════════════════════════════════════════════
```

**EXIT CRITERIA:** Artifact written. Run /critique to review and commit to DB.

</workflow>

<rules>
- 5+ files = route to /plan, not task
- MUST spawn plan-explorer to validate paths — no skipping
- Reject any criterion containing vague patterns
- Default to inbox epic with confirmation when no epic specified
- No DB commit here — /critique reviews and commits when READY
</rules>
