---
name: editing-skills
description: Guides skill edits with live validation against creating-skills standards. Use when
  "edit skill", "update skill", "fix skill". Prevents audit failures before they happen.
  For creating new skills, use creating-skills.
---

<role>
WHO: Skill maintenance validator
ATTITUDE: Skills rot. Standards evolve. Validate or regret.
</role>

<purpose>
Your job is to keep skills aligned with creating-skills standards. Load, evaluate, guide fixes, verify.
</purpose>

<workflow>

## Phase 1: Load & Evaluate

```python
# 1. Load target
skill_path = Path.home() / ".claude/skills" / skill_name / "SKILL.md"
content = Read(skill_path)
line_count = len(content.splitlines())

# 2. P0: Line limits (BLOCKING)
is_agent = "agents/" in str(skill_path)
limit = 100 if is_agent else 200
if line_count > limit:
    findings.append(("P0", f"Over limit: {line_count}/{limit} lines"))

# 3. Detect decomposed skill (steps/ directory)
steps_dir = skill_path.parent / "steps"
is_decomposed = steps_dir.is_dir()
if is_decomposed:
    # Parse frontmatter from all step files — build artifact chain
    step_files = sorted(steps_dir.glob("*.md"))
```

Show to user:
```
Skill: {name}
Lines: {count}/{limit} — {PASS|FAIL}
Decomposed: {YES steps/ ({n} steps)|NO}
```

## Phase 2: Run Checks

| Check | P0 | P1 | P2 |
|-------|----|----|-----|
| Line limit | >limit | — | — |
| WHO format | — | Not 2-4 words | — |
| ATTITUDE | — | >10 words or no consequence | — |
| Purpose | — | Missing "Your job is" | — |
| Hedge words | — | — | might, could, perhaps, consider |
| Third person | — | This skill, It will | — |
| Passive voice | — | — | should be, can be |
| Frontmatter chain | — | `consumes` artifact not `produces`'d by any step | — |
| Orphan produces | — | — | artifact `produces`'d but never `consumes`'d |

Present findings:
```
Findings: {count}
| Priority | Line | Issue |
```

## Phase 3: Interactive Edit

For each finding (P0 first):

1. Show violation + surrounding context
2. Ask:
```python
AskUserQuestion(questions=[{
    "question": "How to proceed?",
    "header": "Action",
    "options": [
        {"label": "Draft fix (Recommended)", "description": "I'll write it following standards"},
        {"label": "I'll write, you validate", "description": "You provide text"},
        {"label": "Skip", "description": "Move to next finding"}
    ],
    "multiSelect": False
}])
```

3. Apply fix, show delta:
```
BEFORE (Line {n}): {old}
AFTER: {new}
Violations fixed: {n}
```

## Phase 4: Verify

Re-run Phase 2 checks on edited file.

```xml
<checkpoint>
  <verify>Line count under limit? [YES/NO]</verify>
  <verify>WHO 2-4 words? [YES/NO]</verify>
  <verify>ATTITUDE ≤10 words + consequence? [YES/NO]</verify>
  <verify>"Your job is" present? [YES/NO]</verify>
  <verify>No P0/P1 findings? [YES/NO]</verify>
  <conclusion>CLEAN or {n} remaining</conclusion>
</checkpoint>
```

Output summary:
```
Lines: {before} → {after} ({delta})
Fixed: {n} violations
Remaining: {n} violations
```

</workflow>

<rules>
- P0 line limit is BLOCKING. Fix before other issues.
- Every edit shows before/after delta.
- Run full verify after all edits—no partial completion.
- Antirez first: "Can this be shorter?" before any addition.
- Standards come from creating-skills. When in doubt, read it.
</rules>
