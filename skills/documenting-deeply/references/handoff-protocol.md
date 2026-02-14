# Handoff Protocol

Requirements for handoff files that enable fresh context to continue documentation.

## Why Handoffs Matter

Deep documentation exhausts context windows. Without proper handoffs:
- Work is lost when context resets
- Comprehension must restart from scratch
- Verification results lost

**Goal:** Any phase output can be read by fresh Claude and continued without loss.

---

## Handoff File Requirements

### 1. Self-Contained

Every handoff MUST include all context needed to continue.

**BAD:**
```markdown
As discussed above, the validators module needs documentation.
See previous analysis for the purpose.
```

**GOOD:**
```markdown
## Target: validators/
**Path:** `/Users/dev/project/formaltask/validators/`
**Purpose:** PreToolUse and PostToolUse validation hooks
**Files:** 5 Python files, 1,200 total lines
**Current docs:** None (gap identified in Phase 1)
```

### 2. Evidence Embedded

All findings must include actual evidence, not references.

**BAD:**
```markdown
The TDDValidator enforces test-first workflow.
```

**GOOD:**
```markdown
### TDDValidator

**Location:** `validators/tdd_validator.py:15-89`
**Purpose:** Blocks Write/Edit operations without failing test

**Key behavior:**
```python
# tdd_validator.py:45-52
def validate(self, tool_use):
    if tool_use.name in ["Write", "Edit"]:
        if not self._has_failing_test():
            return ValidationResult.BLOCK, "Write test first"
    return ValidationResult.ALLOW, None
```

**Edge case:** Skips validation for test files (line 38)
```

### 3. Complete State

Include everything needed to know where we are.

```json
{
  "target_path": "/Users/dev/project/formaltask/validators",
  "skill": "documenting-deeply",
  "working_dir": "~/projects/documenting-deeply/2025-01-20-validators/",
  "current_phase": 4,
  "phases_complete": [
    "doc-discovery",
    "focus-selection",
    "comprehension"
  ],
  "target_doc": "formaltask/README.md#validators",
  "doc_type": "section",
  "started_at": "2025-01-20T10:00:00Z",
  "last_updated": "2025-01-20T11:30:00Z"
}
```

### 4. Resumable

A fresh context should be able to:
1. Read `00-state.json` to understand progress
2. Read the last complete phase output
3. Continue from exactly where work stopped

---

## File Naming Convention

```
{working_dir}/
├── 00-state.json              # Always current state
├── 01-doc-discovery.md        # Phase 1 output
├── 02-focus-selection.md      # Phase 2 output
├── 03-comprehension.md        # Phase 3 output
├── 04-gap-analysis.md         # Phase 4 output
├── 05-readme-draft.md         # Phase 5 output (README content)
├── 05-claudemd-draft.md       # Phase 5 output (CLAUDE.md content)
├── 06-verification.md         # Phase 6 output
└── final/                     # Phase 7 output
    ├── README.md              # Final README (or section content)
    └── CLAUDE.md              # Final CLAUDE.md
```

**Rule:** If file exists, phase is complete. Check state.json for partial progress.

---

## Handoff Checklist

Before considering a phase complete:

- [ ] All file references include file:line
- [ ] All code quotes are actual code (not paraphrased)
- [ ] No references to "above" or "previous"
- [ ] State file updated
- [ ] Fresh Claude could continue from this file alone
- [ ] Target documentation clearly identified

---

## Resume Protocol

When resuming from handoff:

```python
# 1. Read state
state = safe_load(Read(f"{working_dir}/00-state.json"))

# 2. Determine current phase
phase = state["current_phase"]

# 3. Read relevant handoff(s)
if phase == 5:
    # Writing phase - need comprehension and gap analysis
    comprehension = Read(f"{working_dir}/03-comprehension.md")
    gap_analysis = Read(f"{working_dir}/04-gap-analysis.md")

elif phase == 6:
    # Verification phase - need drafts
    readme_draft = Read(f"{working_dir}/05-readme-draft.md")
    claudemd_draft = Read(f"{working_dir}/05-claudemd-draft.md")

# 4. Continue with full context from handoffs
```

---

## Common Handoff Failures

| Failure | Symptom | Prevention |
|---------|---------|------------|
| Missing target | "What are we documenting?" | Embed target path in every handoff |
| Lost comprehension | "What does this code do?" | Include key insights in gap analysis |
| Broken references | "See above" | Never reference prior conversation |
| Stale state | Wrong phase resumed | Update state.json after every step |
| Missing doc type | "README or section?" | Include target_doc and doc_type in state |
