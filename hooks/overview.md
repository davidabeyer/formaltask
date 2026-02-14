---
title: Hooks Overview
description: Understanding the hook system - automated actions that trigger on events
---

# Hooks Overview

Hooks are automated scripts that execute in response to specific events in Claude Code. This setup includes **8 intelligent hooks** that provide workflow automation, context capture, and state management.

## What Are Hooks?

Hooks are shell scripts that run automatically when certain events occur:

- **UserPromptSubmit** - After you send a message
- **PostToolUse** - After Claude uses a tool
- **PreSlashCommand** - Before a slash command runs
- **PostSlashCommand** - After a slash command completes

**Key Feature:** Hooks run **without manual invocation**. You don't call them - they just work.

## Hook Architecture

```
Event Occurs
    ↓
Claude Code checks ~/.claude/settings.json
    ↓
Finds matching hook configuration
    ↓
Executes hook script
    ↓
Hook reads state (SQLite, JSON files)
    ↓
Hook performs actions (update files, call MCPs, etc.)
    ↓
Hook updates state
    ↓
Returns success/failure
    ↓
Claude Code continues
```

## Hook Categories

### Core Hooks (4 hooks)
Essential hooks that provide fundamental automation:

**[user-keyword-reminder](/hooks/core/user-keyword-reminder)**
- **Trigger:** UserPromptSubmit
- **Purpose:** Detects keywords and suggests context capture
- **Features:** Workflow-aware suggestions, dead-end detection, pattern matching

**[dashboard-hook](/hooks/core/dashboard-hook)**
- **Trigger:** PostToolUse
- **Purpose:** Auto-updates activity dashboard after tool calls
- **Features:** Real-time stats, 7-day timeline, active sessions tracking

### Specialized Hooks (4 hooks)
Task-specific hooks for particular workflows:

**[check-git-clean](/hooks/specialized/check-git-clean)**
- **Trigger:** PreSlashCommand (specific commands)
- **Purpose:** Ensures clean git state before operations
- **Use case:** Prevents accidental loss of uncommitted work

**[generate-commit-message](/hooks/specialized/generate-commit-message)**
- **Trigger:** Manual invocation via command
- **Purpose:** AI-generated conventional commit messages
- **Use case:** Consistent commit message format

**[post-slash-command-validator](/hooks/specialized/post-slash-command-validator)**
- **Trigger:** PostSlashCommand
- **Purpose:** Validates command execution results
- **Use case:** Catch failures, log errors

**[pre-compact-checkpoint](/hooks/specialized/pre-compact-checkpoint)**
- **Trigger:** Before memory compaction
- **Purpose:** Creates backup before destructive operations
- **Use case:** Safety net for memory operations

**[property-test-validator](/hooks/specialized/property-test-validator)**
- **Trigger:** After test generation
- **Purpose:** Validates property-based test quality
- **Use case:** Ensures tests are legitimate

## Hook Lifecycle

### 1. Event Occurs
```bash
# User sends message
You: "I tried Redis but it didn't work"
```

### 2. Hook Triggers
```bash
# UserPromptSubmit event fires
# Claude Code checks settings.json for matching hooks
```

### 3. Pattern Matching
```bash
# user-keyword-reminder.sh executes
# Detects pattern: "didn't work"
# Identifies as: dead-end detection
```

### 4. Context Loading
```bash
# Hook queries SQLite for session info
current_workflow=$(sqlite3 ~/claude.db "SELECT workflow FROM sessions WHERE active=1")
# Returns: "debugging"
```

### 5. Action Execution
```bash
# Hook generates workflow-specific suggestion
# Displays formatted reminder to capture dead end
```

### 6. State Persistence
```bash
# Hook logs execution
# Updates hook run history
```

## Hook Configuration

Hooks are configured in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "command": "~/.claude/hooks/user-keyword-reminder.sh",
        "pattern": "(didn't work|failed|dead end|blocked)",
        "timeout": 5000,
        "continueOnError": true
      }
    ],
    "PostToolUse": [
      {
        "command": "~/.claude/hooks/update-dashboard.sh",
        "timeout": 3000
      }
    ]
  }
}
```

**Configuration Options:**
- `command` - Path to hook script
- `pattern` - Regex for UserPromptSubmit filtering (optional)
- `timeout` - Max execution time in milliseconds
- `continueOnError` - Whether to continue if hook fails

## Hook Features

### Workflow-Aware Suggestions

Hooks adapt behavior based on current workflow:

**Debugging Workflow:**
```
You: "Found the bug - race condition in auth module"
Hook: "Suggested capture:
       key='bug-found-auth-race'
       value='[bug description] | [root cause] | [fix applied]'
       category='bug-fix'"
```

**Research Workflow:**
```
You: "Evaluated Redis vs Memcached for caching"
Hook: "Suggested capture:
       key='tech-eval-redis-memcached'
       value='[comparison] | [chosen: Redis] | [rationale]'
       category='tech-decision'"
```

### Dead End Detection

Special pattern for capturing failed approaches:

**Triggers:**
- "didn't work"
- "failed"
- "dead end"
- "blocked"
- "can't proceed"

**Suggestion Format:**
```
key='dead-end-[approach]'
value='[what tried] | [why failed] | [what learned] | [why not retry]'
category='warning'
priority='high'
```

### Auto-Dashboard Updates

The dashboard hook updates after every tool use:

**Updated Sections:**
- Current session name and stats
- This week's capture totals
- 7-day activity timeline
- Active sessions list

**Update Frequency:** After every `mcp__memory-keeper__context_save()` call

## Hook State Management

Hooks maintain state in multiple locations:

### SQLite Database (`~/claude.db`)
```sql
-- Sessions table
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    name TEXT,
    workflow TEXT,
    active INTEGER,
    created_at TIMESTAMP
);

-- Items table
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    key TEXT,
    value TEXT,
    category TEXT,
    priority TEXT,
    created_at TIMESTAMP
);
```

### JSON Cache (`~/.claude/dashboard.json`)
```json
{
  "current_session": {
    "name": "debugging",
    "item_count": 12,
    "last_active": "2025-11-11T10:30:00Z"
  },
  "this_week": {
    "total": 47,
    "by_category": {
      "decision": 8,
      "insight": 15,
      "blocker": 3
    }
  }
}
```

### Log Files (`~/.claude/hooks/logs/`)
```
update-dashboard-2025-11-11.log
user-keyword-reminder-2025-11-11.log
```

## Hook Best Practices

### Design Principles
- **Fast execution** - Hooks should complete in <1 second
- **Idempotent** - Safe to run multiple times
- **Fail gracefully** - Never crash Claude Code
- **Log everything** - Debug with logs, not echo statements

### Error Handling
```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars

# Wrap critical sections
if ! result=$(sqlite3 ~/claude.db "SELECT..."); then
    echo "ERROR: Database query failed" >&2
    exit 1
fi
```

### Performance
```bash
# Use SQLite views for complex queries
# Cache expensive operations
# Avoid external network calls
# Timeout after 5 seconds max
```

### State Consistency
```bash
# Always use transactions for database updates
sqlite3 ~/claude.db <<EOF
BEGIN TRANSACTION;
UPDATE sessions SET active=0 WHERE id != $new_session_id;
UPDATE sessions SET active=1 WHERE id = $new_session_id;
COMMIT;
EOF
```

## Debugging Hooks

### Check Hook Logs
```bash
# View recent hook executions
tail -f ~/.claude/hooks/logs/update-dashboard-*.log

# Search for errors
grep ERROR ~/.claude/hooks/logs/*.log
```

### Test Hook Manually
```bash
# Run hook script directly
bash ~/.claude/hooks/user-keyword-reminder.sh "test input"

# Check exit code
echo $?  # Should be 0 for success
```

### Verify Hook Configuration
```bash
# Check settings.json syntax
cat ~/.claude/settings.json | jq .

# Verify hook file exists
ls -la ~/.claude/hooks/user-keyword-reminder.sh
```

### Common Issues

**Hook doesn't trigger:**
- Check pattern regex in settings.json
- Verify hook script has execute permissions: `chmod +x hook.sh`
- Check Claude Code logs for hook errors

**Hook times out:**
- Reduce timeout in settings.json
- Optimize slow operations (database queries, file I/O)
- Add caching for expensive operations

**Hook fails silently:**
- Check logs in `~/.claude/hooks/logs/`
- Add debug output: `echo "DEBUG: checkpoint" >&2`
- Test hook manually with representative input

## Creating Custom Hooks

Want to build your own hook? See:
- [Hook API](/api/hook-api) - Technical reference
- [Customization Guide](/guides/customization) - Step-by-step tutorial
- [Testing](/api/testing) - How to test hooks

### Example Hook Template

```bash
#!/bin/bash
set -euo pipefail

# Parse input (varies by hook type)
user_input="$1"

# Load state
session_id=$(sqlite3 ~/claude.db "SELECT id FROM sessions WHERE active=1")

# Perform action
if [[ "$user_input" =~ pattern ]]; then
    echo "SYSTEM REMINDER: Matched pattern" >&2
    # Take action
fi

# Update state
sqlite3 ~/claude.db "INSERT INTO hook_runs ..."

# Exit success
exit 0
```

## Next Steps

Explore specific hooks:
- [Core Hooks](/hooks/core/user-keyword-reminder)
- [Specialized Hooks](/hooks/specialized/check-git-clean)

Or learn about:
- [Commands](/commands/overview) - Slash command system
- [MCPs](/mcps/overview) - External integrations
- [Automation](/automation/overview) - Complete automation architecture
