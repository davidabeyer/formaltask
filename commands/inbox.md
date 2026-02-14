---
description: "View blocked workers and help them continue"
allowed-tools: Bash, Read
---

# Inbox

## Step 1: Get Blocked Workers

```bash
python3 -c "
from formaltask.db.path import get_db_path
from formaltask.workers.inbox import get_blocked_workers
import json
db_path = str(get_db_path())
workers = get_blocked_workers(db_path)
print(json.dumps(workers, indent=2))
"
```

Returns: `task_id`, `task_title`, `pending_question`, `blocked_summary`, `age_seconds`

## Step 2: Display

No workers → "No blocked workers." and stop.

Otherwise, show table: task ID, title, age, pending question.

## Step 3: Select Worker

AskUserQuestion with one option per worker (label: "#{id} - {title}"). Include "Skip" option.

If Skip or empty → end workflow.

## Step 4: Get Answer

Show full pending question, then AskUserQuestion:
- "Approve / Proceed as suggested"
- "Reject / Try different approach"
- "Need more context first"

User typically selects "Other" for detailed answer.

## Step 5: Resume Worker

```bash
tmux has-session -t task-$TASK_ID 2>/dev/null && echo "alive" || echo "dead"
```

**If alive:** Tell user to attach manually: `tmux attach -t task-$TASK_ID`

**If dead:** Resume with answer:
```bash
ft resume $TASK_ID -m "$USER_ANSWER"
```
Then: `tmux attach -t task-$TASK_ID`
