---
consumes: [target-type, target-content]
produces: [task-verdict]
---

# TASK PATH

Complete task critique workflow. If target_type == TASK, follow these steps then STOP.

---

## Step 0: Detect Existing Task Context

Check for `.task/id` file in current directory to determine if critiquing for an existing task:

```bash
# Read task ID if in existing-task context
cat .task/id 2>/dev/null
```

- **If `.task/id` exists:** task_id = content, mode = "existing-task"
- **If `.task/id` does not exist:** mode = "new-task" (standalone critique)

---

## Step 1: Verify Task Paths + Context

Verify task claims directly using MCP tools:

```python
# 1. File exists at claimed paths?
for path in files_to_modify:
    Glob(pattern=path)  # Must find file

# 2. Line numbers accurate?
for path, lines in files_with_lines:
    Read(file_path=path, offset=line, limit=10)  # Check claimed content

# 3. Context symbols exist?
for symbol in context_symbols:
    mcp__morph-mcp__warpgrep_codebase_search(
        repo_path="{project_root}",
        search_string=symbol
    )

# 4. Criteria fix stated problem? (human judgment)
# 5. Simpler approach exists? (human judgment)
```

**Verdict:** READY if paths exist, lines accurate, symbols found. NEEDS_WORK if claims false. Ask user about simplicity if uncertain.

## Step 2: Commit or Report

**If READY:**
```python
from formaltask.tasks.crud import create_task

task_id = create_task(
    db_path='.claude/formaltask.db',
    epic_name=epic,
    title=title,
    description=goal,
    criteria=criteria,
    metadata={
        'artifact_type': 'spec',
        'artifact_content': spec_content,
        'required_reviews': required_reviews,
        'documentation_required': doc_required
    }
)
```

**Output:**
```
══════════════════════════════════════════════════════════════
   COMMITTED: #{task_id} - {title}
══════════════════════════════════════════════════════════════
Epic: {epic}
Reviews: {required_reviews}

Ready to spawn: ft work spawn {task_id}
══════════════════════════════════════════════════════════════
```

**If NEEDS_WORK or NOT_NEEDED:**
```
══════════════════════════════════════════════════════════════
   NOT COMMITTED: {verdict}
══════════════════════════════════════════════════════════════
{blockers}

Fix artifact and re-run: /critique {artifact_dir}
══════════════════════════════════════════════════════════════
```

## Step 3: Store Review (Existing-Task Mode Only)

**If mode == "existing-task"** (`.task/id` exists):

After completing your critique, store the review for the task:

```bash
ft review store '{"task_id": <task_id>, "review_type": "code-quality", "severity": "<clean|minor|major|critical>", "summary": "<brief summary of critique verdict>", "findings": [...]}'
```

**Severity mapping:**
- READY → `"clean"`
- NEEDS_WORK (1-2 issues) → `"minor"`
- NEEDS_WORK (3+ issues) → `"major"`
- NOT_NEEDED → `"critical"`

**Output for existing-task mode:**
```
Review stored for task <task_id>.
If verdict is clean: Run `ft task complete <task_id>`
If findings exist: Address findings and re-run critique.
```

**STOP** — task path complete.
