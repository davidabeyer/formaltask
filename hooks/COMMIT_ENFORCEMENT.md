# Commit Enforcement in FormalTask Workflow

## Overview

FormalTask now enforces proper git hygiene by requiring commits before completing issues and preventing new issues from starting with uncommitted changes.

## Enforcement Points

### 1. Task Completion (`/pm-task-complete`)

**Requirement**: All changes must be committed before closing an issue.

**Behavior**:
- Checks for uncommitted changes using `git status --porcelain`
- If uncommitted changes detected:
  - Generates suggested commit message from issue details
  - Includes agent work summary from completion reports
  - Provides copy-paste command to commit
  - Skips closing the issue until committed

**Example Output**:
```
❌ ERROR: uncommitted changes detected

Please commit your work before proceeding:

 M hooks/post-slash-state-updater.sh
 M hooks/tests/test_post_slash_state_updater.bats

💡 You must commit your work before completing this issue.

Suggested commit message:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
feat: Add GitHub label automation for epic phase transitions

Resolves #126

Implemented automatic GitHub issue label updates when epics
transition between phases in the FormalTask workflow.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2. Task Start (`/pm-task-start`)

**Requirement**: Working directory must be clean before starting new issue.

**Behavior**:
- Checks for uncommitted changes before starting work
- If uncommitted changes detected:
  - Blocks starting new issue
  - Suggests completing previous issue or committing manually
  - Provides clear error message

**Example Output**:
```
❌ ERROR: You have uncommitted changes from previous work

Please commit or complete the previous issue first:
  - To commit: git add -A && git commit -m "your message"
  - To complete previous task: /pm-task-complete <task_num>
```

## Commit Message Format

Generated commit messages follow this structure:

```
<type>: <issue title>

Resolves #<issue_num>

<agent work summary from completion reports>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Commit Types (Auto-Detected from Issue Title)

| Issue Title Starts With | Commit Type |
|------------------------|-------------|
| Add, Implement, Create | `feat` |
| Update, Modify, Change | `chore` |
| Remove, Delete | `refactor` |
| Fix (or anything else) | `fix` |

## Helper Scripts

### `hooks/check-git-clean.sh`

Checks for uncommitted changes in working directory.

**Usage**:
```bash
bash hooks/check-git-clean.sh
```

**Exit Codes**:
- `0`: Clean working directory
- `1`: Uncommitted changes detected

### `hooks/generate-commit-message.sh`

Generates formatted commit message from issue details.

**Usage**:
```bash
bash hooks/generate-commit-message.sh <issue_num> <issue_title> [epic_dir]
```

**Parameters**:
- `issue_num`: GitHub issue number
- `issue_title`: Issue title text
- `epic_dir`: Optional path to epic directory (for agent summaries)

**Output**: Formatted commit message to stdout

## Benefits

1. **Traceability** - Each commit maps to specific issue work
2. **Reversibility** - Easy to revert issue-specific changes
3. **PR Quality** - PRs contain actual committed code
4. **Git History** - Clean, issue-scoped commits instead of massive merges
5. **Context** - Commit messages document what changed and why
6. **Automation** - No manual commit message writing needed

## Testing

Full BATS test suite in `hooks/tests/test_commit_enforcement.bats`:

```bash
# Run tests
export PROJECT_ROOT=/path/to/project
bats hooks/tests/test_commit_enforcement.bats
```

**Test Coverage**:
- ✅ Detects uncommitted changes
- ✅ Passes when working directory is clean
- ✅ Detects untracked files
- ✅ Generates proper commit message format
- ✅ Includes agent work summaries

## Workflow Example

```bash
# Start work on issue
/pm-task-start 126

# ... do work, modify files ...

# Try to complete task (will be blocked)
/pm-task-complete 126
# ❌ ERROR: uncommitted changes detected
# 💡 Suggested commit message shown

# Commit using suggested message
git add -A && git commit -m "feat: Add label automation

Resolves #126"

# Now complete the task
/pm-task-complete 126
# ✅ Closed successfully

# Start next task (now allowed since committed)
/pm-task-start 127
# ✅ Proceeds with issue start
```

## Integration with TDD Guard

Commit enforcement works alongside TDD Guard:

1. **TDD Guard**: Ensures tests exist and pass before committing
2. **Commit Enforcement**: Ensures commits happen per issue

Both systems prevent:
- Committing untested code
- Completing issues without commits
- Starting new work with uncommitted changes

## Future Enhancements

Potential additions:
- Automatic branch creation per issue
- Commit message templates per issue type
- Integration with PR creation workflow
- Commit message validation (conventional commits)
- Automatic tagging of commits with issue labels
