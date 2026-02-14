---
consumes: [audit-target]
produces: [audit-findings]
---

## Mark In-Progress

**IMMEDIATELY** edit `ANTIREZ_AUDIT.md`: `[ ]` -> `[~]`

## Read Entire File

No skimming. Full context required.

## Question File Existence FIRST

Apply checklists from `references/audit-checklists.md`:
- File existence check
- The praise test

## Function Breakdown Table (MANDATORY)

Every function gets a row:

| Function | LOC | Verdict | Evidence | Quality |
|----------|-----|---------|----------|---------|
| `_foo()` | 45 | DELETE | Zero callers | -- |
| `bar()` | 12 | KEEP | Core logic | ok |
| `_baz()` | 8 | INLINE | Single caller | Nested 4 deep |

**Verdicts:** DELETE, INLINE, SIMPLIFY, KEEP

**Boundaries:** `grep -n '^    def ' {file}` -> subtract lines.

## Apply Checklists

From `references/audit-checklists.md`:
- Deletion checklist
- Quality smells (findings go in Quality column)

## Envision Beautiful Alternative

After identifying deletions, show what REMAINS looks like:
```
Before: 6 functions, 200 LOC, 3 abstractions
After:  2 functions, 50 LOC, direct code
```
