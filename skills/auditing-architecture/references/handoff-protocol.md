# Handoff Protocol

Requirements for handoff files that enable fresh context to continue analysis.

## Why Handoffs Matter

Deep analysis exhausts context windows. Without proper handoffs:
- Work is lost when context resets
- Analysis must restart from scratch
- Findings lose their evidence chain

**Goal:** Any phase output can be read by fresh Claude and continued without loss.

---

## Handoff File Requirements

### 1. Self-Contained

Every handoff MUST include all context needed to continue.

**BAD:**
```markdown
As discussed above, the `api` module has issues.
See previous analysis for details.
```

**GOOD:**
```markdown
## Module: api/
**Path:** `/path/to/project/api/`
**Purpose:** HTTP request handling and routing
**Key files:** `routes.py` (450 lines), `handlers.py` (320 lines)
**Analysis:** [complete details embedded here]
```

### 2. Evidence Embedded

All findings must include actual evidence, not references.

**BAD:**
```markdown
The `process_request` function has issues.
```

**GOOD:**
```markdown
### Finding: Silent error swallowing in process_request

**Location:** `api/handlers.py:45-67`

**Current code:**
```python
def process_request(data):
    try:
        result = do_work(data)
    except Exception:
        return None  # Silently swallows ALL exceptions
    return result
```

**The problem:** All exceptions (including programming errors like TypeError)
are caught and converted to None, making debugging impossible.

**Proposed fix:**
```python
def process_request(data: dict) -> Result | None:
    try:
        result = do_work(data)
    except ValidationError as e:
        logger.warning("Validation failed: %s", e)
        return None
    except Exception:
        logger.exception("Unexpected error in process_request")
        raise
    return result
```

**Why this is a problem:** TypeError, AttributeError silently become None.
```

### 3. Complete State

Include everything needed to know where we are.

```json
{
  "target_path": "/Users/dev/project",
  "skill": "auditing-code-deeply",
  "working_dir": "~/projects/auditing-code-deeply/2025-01-17-project-name/",
  "current_phase": 3,
  "phases_complete": [
    "architecture-mapping",
    "module-selection"
  ],
  "selected_modules": [
    {"name": "api", "path": "src/api/", "status": "complete"},
    {"name": "core", "path": "src/core/", "status": "in_progress"},
    {"name": "utils", "path": "src/utils/", "status": "pending"}
  ],
  "findings_count": 7,
  "started_at": "2025-01-17T10:00:00Z",
  "last_updated": "2025-01-17T11:30:00Z"
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
├── 00-state.json                    # Always current state
├── 01-architecture-mapping.md       # Phase 1 (complete when exists)
├── 02-module-selection.md           # Phase 2 (complete when exists)
├── 03-module-api-analysis.md        # Phase 3 - module "api"
├── 03-module-core-analysis.md       # Phase 3 - module "core"
├── 03-module-utils-analysis.md      # Phase 3 - module "utils"
├── 04-verified-findings.md          # Phase 4 (complete when exists)
└── 05-final-report.md               # Phase 5 (complete when exists)
```

**Rule:** If file exists, phase is complete. Check state.json for partial progress.

---

## Handoff Checklist

Before considering a phase complete:

- [ ] All code references include file:line
- [ ] All code quotes are actual code (not paraphrased)
- [ ] No references to "above" or "previous"
- [ ] State file updated
- [ ] Fresh Claude could continue from this file alone

---

## Resume Protocol

When resuming from handoff:

```python
# 1. Read state
state = safe_load(Read(f"{working_dir}/00-state.json"))

# 2. Determine current phase
phase = state["current_phase"]

# 3. Read relevant handoff(s)
if phase == 3:
    # Module analysis in progress
    architecture = Read(f"{working_dir}/01-architecture-mapping.md")
    selection = Read(f"{working_dir}/02-module-selection.md")

    # Find next module
    for module in state["selected_modules"]:
        if module["status"] == "pending":
            # Continue with this module
            break

# 4. Continue analysis with full context from handoffs
```

---

## Common Handoff Failures

| Failure | Symptom | Prevention |
|---------|---------|------------|
| Missing context | "What module was this?" | Embed module name/path in every finding |
| Lost evidence | "Where was this code?" | Include file:line and actual quotes |
| Broken references | "See above" | Never reference prior conversation |
| Stale state | Wrong phase resumed | Update state.json after every step |
| Incomplete findings | Can't verify | Include reasoning, not just conclusion |
