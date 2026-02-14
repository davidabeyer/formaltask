---
name: reflect
description: Forces reflection before task completion. Prompts self-reflection FIRST,
  then shows sibling specs. Mandatory when CHECK_LEARNINGS enabled.
---

<role>
WHO: Knowledge extractor
ATTITUDE: You learned something. Spit it out before you forget.
</role>

<purpose>
Extract learnings BEFORE showing context. Seeing siblings first contaminates your memory. Think, then share.
</purpose>

<workflow>

## 1. Context

```bash
echo "TASK_ID: $TASK_ID"
```

No TASK_ID? Stop: "Run from worker session."

## 2. Extract (BEFORE siblings)

```
## WHAT DID YOU LEARN?

Answer before seeing sibling tasks:

| Question | Why |
|----------|-----|
| What surprised you? | Edge cases, gotchas, dragons |
| What's NOT in the spec? | Implicit knowledge you had to discover |
| What would you tell past-you? | Warnings, shortcuts, patterns |
| [SPEC] How could the spec be better? | Planning feedback |

Write it down. NOW.
```

## 3. Query Siblings

```bash
sqlite3 "$PROJECT_ROOT/.claude/formaltask.db" "
SELECT id, title, json_extract(metadata, '$.artifact_content') as spec
FROM tasks
WHERE epic_name = (SELECT epic_name FROM tasks WHERE id = $TASK_ID)
AND id != $TASK_ID
AND status NOT IN ('completed', 'cancelled')
"
```

## 4. Show Siblings

For each:
```
---
### Task #<id>: <title>
<spec or "(No spec)">
```

List IDs comma-separated.

## 5. Capture

| Situation | Command |
|-----------|---------|
| Helps siblings | `ft learning "insight" --for <ids>` |
| Task-specific only | `ft learning "insight"` |
| Spec feedback | `ft learning "[SPEC] spec was missing X"` |

No siblings? Still capture: `ft learning "insight"`

</workflow>

<rules>
- Extract FIRST. Context SECOND. Order matters.
- Something is better than nothing. Capture it.
- [SPEC] prefix = planning process feedback
- Stop hook blocks until you do this. Don't fight it.
</rules>
