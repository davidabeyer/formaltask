---
consumes: [task-spec]
produces: [task-artifact]
---
# Phase 7-8: Generate & Write Artifact

**BLOCKING GATE:** Reviews and doc flag set in Phase 6.

## Artifact Template

```markdown
# Task: {title}

**Required reviews: {reviews from Phase 6}**
**Documentation required: {true|false from Phase 6}**

## Goal
{One sentence: what this accomplishes}

## Context
Epic: {epic_name}
Discovery: {key findings from Phase 2}

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
- `{file1}:{line}` - {what changes}
- `{file2}:{line}` - {what changes}

## Notes  <!-- optional: implementation guidance, edge cases, risks -->
{Add only if non-obvious from context}
```

## Write to Disk

```python
from pathlib import Path
from datetime import datetime, timezone
import re

date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

artifact_dir = Path.home() / "projects" / "one-offs" / f"{date}-{slug}"
artifact_dir.mkdir(parents=True, exist_ok=True)
(artifact_dir / "task.md").write_text(ARTIFACT_CONTENT)
```

## Output Display

```
═══════════════════════════════════════════════════════════════
   TASK ARTIFACT CREATED
═══════════════════════════════════════════════════════════════

Title: {title}
Epic: {epic_name}
Artifact: {artifact_dir}/task.md

Next: /critique-task {artifact_dir}
      (DB commit happens when verdict is READY)
═══════════════════════════════════════════════════════════════
```

## Exit Criteria

Artifact file written. User informed of next step. No DB commit.
