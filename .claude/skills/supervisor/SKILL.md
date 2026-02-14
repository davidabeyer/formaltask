---
name: supervisor
description: 'Monitor blocked workers and help respond to them. Loop checks ft inbox, shows blocked workers, lets you respond naturally.'
---

<role>Worker Supervisor</role>

<purpose>Poll for blocked workers. Show their questions. Let human respond. Resume worker.</purpose>

---

## Main Loop

**Every invocation and after every action, run this loop:**

### Step 1: Check Inbox

```bash
ft inbox --json
```

Parse the JSON array. Each item has:
- `task_id`: Worker ID
- `task_title`: Task name
- `pending_question`: What they're blocked on
- `age_seconds`: How long blocked

### Step 2: If No Blocked Workers

```
Show: "No blocked workers. Checking again in 30 seconds..."

Wait 30 seconds (just tell user, don't actually sleep)

Ask: "Check again now, or exit?"
  - "Check again" → Step 1
  - "Exit" → End skill
```

### Step 3: If Blocked Workers Exist

For each blocked worker, show:

```
───────────────────────────────────────
BLOCKED: #[task_id] — [task_title]
Waiting: [age in minutes]m

Q: [pending_question]
───────────────────────────────────────
```

Then ask:

```
AskUserQuestion:
  question: "How do you want to respond to #[task_id]?"
  header: "Response"
  options:
    - label: "Continue"
      description: "Tell worker to keep trying"
    - label: "Skip for now"
      description: "Come back to this one later"
```

**If user selects an option:** Map to response message.
**If user types custom text:** Use that as the response.

### Step 4: Resume Worker

```bash
ft resume [task_id] -m "[response message]"
```

Show: "Resumed #[task_id]"

Return to Step 1.

---

## Response Mappings

| Selection | Message |
|-----------|---------|
| Continue | "Continue working on the task. Try a different approach if stuck." |
| Skip for now | (don't resume - just move to next worker) |
| Custom text | User's exact input |

---

## Rules

1. **Always check inbox first** — don't ask what to do, just check
2. **Oldest first** — workers sorted by age, address oldest first
3. **Custom text is the response** — no reformatting, no prefixes
4. **Loop forever** — only exit when user explicitly says "exit" or "quit"
5. **Brief output** — no explanations, just worker info and questions
