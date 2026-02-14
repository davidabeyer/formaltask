# Verification Protocol

How to verify documentation matches actual code behavior.

## Why Verification Matters

Documentation without verification produces:
- Claims that don't match implementation
- Examples that don't work
- File references that don't exist
- Edge cases documented incorrectly

**Goal:** Every claim in documentation must be traceable to code.

---

## Verification Steps

### Step 1: Extract Claims

Read the documentation draft and list every verifiable claim.

**Claim types:**
- Function behavior ("returns X when Y")
- Parameter types ("accepts a string")
- Error conditions ("raises ValueError if...")
- File locations ("implemented in X.py")
- Examples ("this code produces this output")

```markdown
# Claims to Verify

## From README Section: "Task Lifecycle"

1. "Tasks start in 'pending' state" → verify initial state
2. "start_task() transitions to 'in_progress'" → verify method
3. "complete_task() requires task to be in_progress" → verify guard
4. "See task_manager.py:45" → verify file/line exists
```

### Step 2: Find Evidence

For each claim, locate the supporting code.

```python
# Claim: "Tasks start in 'pending' state"
Read("task_manager.py")
# Find: line 23: self.state = TaskState.PENDING

# Claim: "start_task() transitions to 'in_progress'"
Read("task_manager.py")
# Find: line 67: self.state = TaskState.IN_PROGRESS

# Claim: "complete_task() requires task to be in_progress"
Read("task_manager.py")
# Find: line 89: if self.state != TaskState.IN_PROGRESS: raise...
```

### Step 3: Verify Examples

Run or trace every code example to ensure it works.

```python
# Example from docs:
"""
from formaltask import TaskManager
manager = TaskManager()
task = manager.create_task("Test")
manager.start_task(task.id)
"""

# Verify:
# 1. Does TaskManager exist and import correctly?
# 2. Does create_task accept a string argument?
# 3. Does start_task accept task.id?
# 4. Do these calls actually work in sequence?
```

### Step 4: Check Cross-References

Verify all links and file references are valid.

```python
# Reference: "See task_manager.py:45"
Read("task_manager.py", offset=45, limit=10)
# Verify: Does line 45 contain what the docs say?

# Reference: "See also: validators/README.md"
Read("validators/README.md")
# Verify: Does the file exist? Is the section referenced there?
```

---

## Verification Verdicts

For each claim, assign a verdict:

| Verdict | Meaning | Action |
|---------|---------|--------|
| **ACCURATE** | Claim matches code exactly | Keep as-is |
| **INACCURATE** | Claim differs from code | Fix documentation |
| **OUTDATED** | Was true, code changed | Update documentation |
| **UNVERIFIABLE** | Cannot find code to verify | Investigate or remove claim |
| **MISSING CONTEXT** | True but misleading | Add clarification |

---

## Verification Output Format

Write to: `{working_dir}/06-verification.md`

```markdown
# Documentation Verification

## Summary

| Verdict | Count |
|---------|-------|
| Accurate | {n} |
| Inaccurate | {n} |
| Outdated | {n} |
| Unverifiable | {n} |

## Detailed Findings

### Claim 1: "Tasks start in 'pending' state"
**Source:** README.md, line 45
**Verdict:** ACCURATE

**Evidence:**
```python
# task_manager.py:23
def __init__(self):
    self.state = TaskState.PENDING
```

---

### Claim 2: "complete_task() returns the task object"
**Source:** README.md, line 67
**Verdict:** INACCURATE

**Evidence:**
```python
# task_manager.py:95
def complete_task(self):
    self.state = TaskState.COMPLETED
    return None  # Actually returns None, not task
```

**Fix:** Update documentation to say "returns None"

---

### Claim 3: "Configuration in config.yaml"
**Source:** README.md, line 12
**Verdict:** OUTDATED

**Evidence:**
```python
# config.py:5 (as of commit abc123)
CONFIG_FILE = "settings.json"  # Changed from config.yaml
```

**Fix:** Update to "settings.json"

---

## Unverifiable Claims

These claims could not be verified against code:

1. "Performance is optimized for large datasets"
   - No code evidence found
   - **Recommendation:** Remove or qualify the claim

2. "Used by 100+ developers"
   - External claim, cannot verify
   - **Recommendation:** Remove or cite source
```

---

## Example Verification

For code examples, verify they actually work:

```markdown
### Example Verification: "Quick Start"

**Documented example:**
```python
from formaltask import TaskManager

manager = TaskManager()
task = manager.create("My Task")
print(task.status)  # "pending"
```

**Verification:**

1. Import check:
   - `from formaltask import TaskManager` ✓
   - TaskManager is exported in `__init__.py:12`

2. Constructor check:
   - `TaskManager()` ✓
   - No required arguments per `task_manager.py:15`

3. Method check:
   - `manager.create("My Task")` ✗
   - **INACCURATE:** Method is `create_task`, not `create`
   - See `task_manager.py:34`

4. Attribute check:
   - `task.status` ✗
   - **INACCURATE:** Attribute is `task.state`, not `task.status`
   - See `task.py:12`

**Corrected example:**
```python
from formaltask import TaskManager

manager = TaskManager()
task = manager.create_task("My Task")
print(task.state)  # "pending"
```
```

---

## Common Verification Failures

| Failure | Symptom | Prevention |
|---------|---------|------------|
| Trusted the docs | Didn't check code | Verify EVERY claim |
| Checked wrong file | Evidence doesn't match | Verify file:line precisely |
| Skipped examples | Examples broken | Run/trace all examples |
| Assumed links work | 404s in production | Click every link |
| Verified once | Docs drift from code | Re-verify on updates |

---

## Verification Checklist

Before marking documentation complete:

- [ ] Every behavior claim verified against code
- [ ] Every file reference verified to exist
- [ ] Every line number verified to be current
- [ ] Every example verified to work
- [ ] Every cross-reference verified to resolve
- [ ] All inaccuracies fixed or flagged
