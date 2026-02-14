## Phase 1: Load Skill
Skill(skill="review-implementing")

## Phase 2: Findings to Address
{findings_section}

## Phase 3: Implementation
Follow skill workflow: parse, TodoWrite, implement, validate, lint

## Phase 4: Commit
git add -A && git commit -m "fix: address review findings" && git push

## Phase 5: Re-Run Reviews
{review_task_calls}

## Phase 6: Retry Completion
python3 -m formaltask.cli.pm task-complete {task_id}
