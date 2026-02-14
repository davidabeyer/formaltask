# formaltask/review/

Review context management and prompt building for FormalTask code reviews.

## Quick Start

```python
from formaltask.review.context import ReviewContext
from formaltask.review.instructions import build_review_prompt

# Create context from task
ctx = ReviewContext.from_task(task_id=42, db_path=db_path, worktree_path="/path/to/worktree")

# Build review prompt
prompt = build_review_prompt(ctx, review_type="code-quality")
```

## ReviewContext

Unified context for code reviews:

```python
from formaltask.review.context import ReviewContext

ctx = ReviewContext.from_task(
    task_id=42,
    db_path=db_path,
    worktree_path="/path/to/worktree"  # Optional but needed for file change detection
)

# Access review data
print(ctx.title)                      # Task title
print(ctx.review_round)               # Current round (1, 2, 3...)
print(ctx.spec_content)               # Task spec content
print(ctx.acceptance_criteria)        # List of criteria strings
print(ctx.previous_findings)          # Findings from previous rounds
print(ctx.files_changed_since_last_review)  # Files changed since last review
print(ctx.diff_ref)                   # Git ref used for diff (e.g., "sha123..HEAD")
```

### ReviewContext Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | int | Task ID |
| `title` | str | Task title |
| `worktree_path` | str | Path to worktree |
| `spec_content` | str | None | Task spec content |
| `acceptance_criteria` | list[str] | Acceptance criteria |
| `review_round` | int | Current review round |
| `previous_findings` | list[dict] | Findings from previous rounds |
| `files_changed_since_last_review` | list[str] | Changed files |
| `diff_ref` | str | None | Git diff reference |

### Diff Reference Priority

For detecting changed files:
1. `last_review_sha` — Re-review (diff since last review)
2. `starting_sha` — First review (diff since task start)
3. `origin/master` — Fallback

## Review Prompts

Build structured prompts for review agents:

```python
from formaltask.review.instructions import build_review_prompt

# First review
prompt = build_review_prompt(ctx, review_type="code-quality")

# Verification review (round > 1 with findings)
prompt = build_review_prompt(
    ctx,
    review_type="code-quality",
    findings_to_verify=[{"file": "x.py", "message": "Missing error handling"}],
    wontfix_entries=[{"file": "y.py", "line": 10, "reason": "Intentional"}]
)
```

### Prompt Sections

| Section | When Included |
|---------|---------------|
| Spec Content | If `ctx.spec_content` is set |
| Acceptance Criteria | If any criteria exist |
| Wontfix Items | If `wontfix_entries` provided |
| Findings to Verify | If `findings_to_verify` provided |
| Files Changed | If `ctx.files_changed_since_last_review` non-empty |

### Verification Mode

When `review_round > 1` and findings exist, switches to minimal verification prompt:
- Lists previous findings to verify
- Shows only files changed since last review
- Asks for FIXED/NOT_FIXED/PARTIALLY_FIXED per finding

## Review Round Tracker

Track review rounds and query previous findings:

```python
from formaltask.review.round_tracker import ReviewRoundTracker

tracker = ReviewRoundTracker(db_path)

# Get current round (next round to run)
round_num = tracker.get_current_round(task_id)  # Returns 1, 2, 3...

# Get previous findings
findings = tracker.get_previous_findings(task_id)
# Filter by review type
findings = tracker.get_previous_findings(task_id, review_type="code-quality")
# Filter by severity
findings = tracker.get_previous_findings(task_id, severity_filter="P1")
```

## Review Packet Schema

Pydantic schema for review agent output:

```python
from formaltask.review.packet_schema import ReviewPacket

# Validate review agent output
packet = ReviewPacket.model_validate(agent_output)
```

## Key Files

| File | Purpose |
|------|---------|
| `context.py` | `ReviewContext` — unified review context |
| `instructions.py` | `build_review_prompt()` — prompt builder |
| `round_tracker.py` | `ReviewRoundTracker` — round/findings tracking |
| `packet_schema.py` | `ReviewPacket` — output schema |

## Common Gotchas

| Issue | Solution |
|-------|----------|
| Empty `files_changed` | Pass `worktree_path` to `ReviewContext.from_task()` |
| Wrong diff reference | Check `last_review_sha` and `starting_sha` in tasks table |
| "Task not found" | Task ID doesn't exist — raises `TaskNotFoundError` |
| Round not incrementing | Reviews are stored per `review_type` — check filter |

## See Also

- `formaltask/workers/reviewer.py` — Uses ReviewContext for reviews
- `formaltask/state/findings.py` — Findings disposition analysis
- `formaltask/cli/commands/review*.py` — CLI commands for reviews
