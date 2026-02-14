# commands/ - Detailed Documentation

Slash commands for Claude Code. Commands are markdown files that expand into prompts when invoked.

> **Location**: This is the SOURCE directory (`formaltask/commands/`), symlinked to `~/.claude/commands/`.
> Project-specific overrides go in `.claude/commands/` (no CLAUDE.md there - use README.md for docs).

## What Are Commands?

Commands are markdown files that define reusable prompts invoked via `/command-name`. They enable:
- Workflow automation (FormalTask, git operations)
- Standardized processes (code review, research)
- Tool orchestration (CLI wrappers)

## Command Categories

### FormalTask Commands (`/*`)

**Guides & Init:**
| Command | Purpose | Usage |
|---------|---------|-------|
| `/guide` | **Concise workflow guide** (agents start here) | `/guide` |
| `/parallel-help` | Detailed parallel workflow reference | `/parallel-help` |
| `/init` | Initialize database | `/init` |

**Epic Management:**
| Command | Purpose | Usage |
|---------|---------|-------|
| `/epic-list` | List all epics | `/epic-list` |
| `/epic-start` | Start working on epic | `/epic-start auth-system` |
| `/epic-close` | Close completed epic | `/epic-close auth-system` |
| `/epic-decompose` | Break epic into tasks | `/epic-decompose auth-system` |
| `/epic-review` | Code review epic | `/epic-review auth-system` |

**Task Management:**
| Command | Purpose | Usage |
|---------|---------|-------|
| `/worker-spawn` | **Spawn single task worker** (preferred) | `/worker-spawn 42` |
| `/parallel-start` | Spawn all ready tasks in epic | `/parallel-start epic` |
| `/task-start` | Interactive: start task | `/task-start 42` |
| `/task-complete` | Interactive: complete task | `/task-complete 42` |
| `/task-show` | Show task details | `/task-show 42` |
| `/task-close` | Close task | `/task-close 42` |
| `/task-edit` | Edit task | `/task-edit 42` |
| `/task-reopen` | Reopen closed task | `/task-reopen 42` |
| `/task-add` | Add task with discovery + spec | `/task-add epic "title"` |

**Review System:**
| Command | Purpose | Usage |
|---------|---------|-------|
| `/review-fix` | Convert review findings to tasks | `/review-fix epic --dry-run` |

### Development Commands

| Command | Purpose | Usage |
|---------|---------|-------|
| `/build` | Run build process | `/build` |
| `/plan` | Create versioned plan (skill) | `/plan feature-name` |
| `/decompose` | Break plan → specs or specs → tasks (skill) | `/decompose project` |
| `/critique` | Review plans, specs, or tasks (skill) | `/critique project` |
| `/revise` | Fix critique blockers (skill) | `/revise project` |
| `/reflect` | Cross-session pattern analysis | `/reflect` |
| `/plan-status` | Dashboard of all planning projects (skill) | `/plan-status` |

### Planning Workflow

```
/plan {project}              # Create versioned plan
    ↓
/critique {project}          # Review plan (verdict: APPROVED / FIX_AND_SHIP / REVISE)
    ↓
/revise {project}            # Fix blockers (if needed), then re-run /critique
    ↓
/decompose {project}         # Generate specs from approved plan
    ↓
/critique {project}          # Review specs
    ↓
ft epic decompose {project}  # Commit tasks to database
    ↓
ft work spawn --epic {project}  # Spawn workers
```

See [Planning Workflow Reference](../skills/PLANNING-WORKFLOW.md) for the full lifecycle diagram, verdict routing, file layout, and end-to-end example.

**Key insight:** Specs contain detailed implementation blueprints; `epic.yaml` is the simplified task list format parsed by `ft epic decompose`. Specs are the source of truth for implementation details, but `epic.yaml` drives the database commit.

### Review Declarations in Planning

`/decompose` generates epic.yaml files with review declarations per task.

**Syntax in generated epic.yaml tasks:**
```yaml
tasks:
  - title: Task title
    required_reviews:
      - security
      - code-quality
```

**Valid review types:** `code-quality`, `test-quality`, `security`, `perf`, `acceptance`

**Auto-suggestion heuristics** (in epic template comments):
- `security`: Suggest when task mentions auth, login, password, token, payment
- `perf`: Suggest for data processing, caching, database queries
- `test-quality`: Complex business logic or validation code
- `code-quality`: Refactoring tasks or new public APIs
- `acceptance`: User-facing features or workflow changes

See `formaltask/tasks/guards.py` and `formaltask/validators/` for guard enforcement at task completion.

### Critique & Research Commands

| Command | Purpose | Usage |
|---------|---------|-------|
| `/critique` | **Unified critique** (plans, issues, proposals, research) | `/critique plans/auth-v1.md` |
| `/critique` | Issue critique | `/critique 42` |
| `/critique` | Research question | `/critique "JWT vs sessions?"` |
| `/groundcrew` | Fact-check content | `/groundcrew file.md` |
| `/council-review` | Multi-LLM review | `/council-review file.md` |
| `/research/*` | Research topics | `/research/deep-dive topic` |
| `/critique-proposal` | *(Deprecated → use `/critique`)* | `/critique file.md` |
| `/pre-plan` | *(Unified into `/critique`)* | `/critique "question"` |

## Command File Format

```markdown
---
allowed-tools: Bash, Read, Write
---

# Command Title

Brief description.

## Usage
\`\`\`
/command-name <arg>
\`\`\`

## Steps

1. First step
2. Second step

## Implementation

\`\`\`bash
# Code that Claude executes
\`\`\`
```

### YAML Frontmatter Options

| Field | Purpose | Example |
|-------|---------|---------|
| `allowed-tools` | Tools command can use | `Bash, Read, Write` |
| `model` | Preferred model | `claude-sonnet-4-5-20250929` |
| `description` | Shown in /help and required for thin wrapper commands | `"Start a task"` |

## Creating New Commands

1. Create file: `.claude/commands/my-command.md`

2. Add frontmatter and content:

```markdown
---
allowed-tools: Bash, Read
---

# My Command

Does something useful.

## Usage
\`\`\`
/my-command <arg>
\`\`\`

## Implementation

\`\`\`bash
echo "Argument: $ARGUMENTS"
# Your implementation
\`\`\`
```

3. Test: `/my-command test-arg`

4. Add to command table above

## Variable Reference

| Variable | Value |
|----------|-------|
| `$ARGUMENTS` | Everything after command name |
| `$PROJECT_ROOT` | Project root directory |

## CLI Integration

Many `/*` commands wrap Python CLI:

```markdown
## Implementation

\`\`\`bash
ft task-start $ARGUMENTS
\`\`\`
```

This maps to `formaltask/cli/commands/task_start.py`.

### Thin Wrapper Conversion Status

Commands are categorized by complexity and delegation pattern:

| Category | Line Count | Description | Count |
|----------|------------|-------------|-------|
| **Thin Wrapper** | <60 | Pure CLI delegation | 18 |
| **Partial Thin Wrapper** | 60-100 | CLI + post-processing | 6 |
| **Orchestration** | >100 | Complex multi-step logic | 21 |

**Thin Wrappers (<60 lines):**
| Command | Lines | Notes |
|---------|-------|-------|
| `/init`, `/status`, `/next`, `/search` | 6 | Core workflow |
| `/epic-show`, `/epic-status`, `/epic-list` | 6-7 | Epic display |
| `/task-show`, `/task-start`, `/task-complete` | 28-39 | Task workflow |
| `/epic-close`, `/epic-overview` | 38-51 | Epic lifecycle |
| `/review-skip`, `/review-retry`, `/review-status` | 18-24 | Review helpers |
| `/worker-complete`, `/worker-spawn` | 22-26 | Worker commands |
| `/parallel-start` | 59 | Partial thin wrapper borderline |

**Partial Thin Wrappers (60-100 lines):**
| Command | Lines | Notes |
|---------|-------|-------|
| `/dashboard` | 65 | Output formatting |
| `/epic-edit` | 65 | Multi-field editing |
| `/task-reopen`, `/task-edit` | 69-75 | Task editing |
| `/task-status`, `/pr-create` | 78-79 | Status/PR creation |

**Orchestration Commands (>100 lines, intentionally not thin wrappers):**
- See [Exclusions](#exclusions-not-thin-wrappers) for rationale on `/epic-start` and `/parallel-status`
- Commands like `/epic-decompose`, `/task-add`, `/review-fix` require complex multi-agent coordination

### Thin Wrapper Pattern

Commands should delegate logic to the Python CLI (`ft`) rather than containing complex bash or SQL.

#### Full Thin Wrapper Template

For commands with **no post-CLI logic** - just validation and delegation:

```markdown
---
allowed-tools: Bash
description: Start working on a task
---

# Task Start

Start working on a task by ID.

## Usage

\`\`\`
/task-start <task_id>
\`\`\`

## Preflight

![ -n "$ARGUMENTS" ] && [[ "$ARGUMENTS" =~ ^[0-9]+$ ]] && echo '{"valid": true}' || echo '{"error": "Task ID required (numeric)"}'

## Instructions

Run the task-start command:

\`\`\`bash
ft task-start $ARGUMENTS
\`\`\`

The CLI handles validation, dependency checks, and status updates.
```

**Characteristics:**
- ~30 lines or less
- Single CLI call in Instructions section
- All logic in CLI, command just routes

#### Partial Thin Wrapper Template

For commands that need **post-CLI bash processing** (output formatting, follow-up actions):

```markdown
---
allowed-tools: Bash
description: Spawn workers for dependency-ready tasks in an epic
---

# Parallel Start

Spawn task workers in tmux sessions for dependency-ready tasks in an epic.

## Usage

\`\`\`
/parallel-start <epic_name>
\`\`\`

## Preflight

![ -n "$ARGUMENTS" ] && echo '{"valid": true}' || echo '{"error": "Epic name required"}'

## Instructions

Run the spawn command with the epic flag:

\`\`\`bash
ft spawn --epic $ARGUMENTS
\`\`\`

The CLI handles:
1. Finding dependency-ready tasks in the epic
2. Setting task status to `in_progress`
3. Creating git worktrees at `~/.claude/worktrees/task-{id}`
4. Spawning tmux sessions with Claude Code
5. Registering workers in the database

## Post-Spawn Commands

\`\`\`bash
tmux attach -t task-42      # Attach to worker
/dashboard               # TUI monitoring
\`\`\`
```

**Characteristics:**
- 30-60 lines
- CLI call plus helpful output/examples
- No raw SQL or complex bash logic

**Benefits:**
- Reduced command file size (target: <60 lines)
- No raw SQL queries in command files
- Centralized logic in tested CLI modules
- Consistent error handling and output formatting

### Pre-command Execution (`!` Prefix)

Lines starting with `!` execute **before** the main command logic and are used for argument validation (preflight checks).

**Syntax:**
```bash
![ -n "$ARGUMENTS" ] && echo '{"valid": true}' || echo '{"error": "Argument required"}'
```

**How it works:**
1. Claude evaluates the `!` line first
2. If output contains `{"error": ...}`, command execution stops with the error message
3. If output contains `{"valid": true}`, execution continues to main Instructions
4. Multiple `!` lines execute in order (first error stops execution)

**Common validation patterns:**
```bash
# Required argument
![ -n "$ARGUMENTS" ] && echo '{"valid": true}' || echo '{"error": "Argument required"}'

# Numeric ID required
![ -n "$ARGUMENTS" ] && [[ "$ARGUMENTS" =~ ^[0-9]+$ ]] && echo '{"valid": true}' || echo '{"error": "Numeric task ID required"}'

# File must exist
![ -f "$ARGUMENTS" ] && echo '{"valid": true}' || echo '{"error": "File not found: $ARGUMENTS"}'
```

### Error Handling (Non-JSON Output)

When CLI commands produce non-JSON output (plain text, markdown tables), the command file should:

1. **Trust CLI error handling**: Let the CLI raise exceptions with clear messages
2. **Don't parse output**: Avoid parsing CLI output for success/failure
3. **Use exit codes**: CLI returns non-zero on failure

```markdown
## Instructions

\`\`\`bash
ft task-show $ARGUMENTS
\`\`\`

If the task doesn't exist, the CLI will output an error message directly.

## Testing Commands

1. **Invoke test**: Run `/my-command test` - verify execution
2. **Argument test**: Various inputs - verify parsing
3. **Error test**: Invalid inputs - verify error messages
4. **Integration test**: Full workflow - verify end-to-end

### Thin Wrapper Testing Standards

For commands converted to thin wrappers, add BATS tests to `hooks/tests/bats/test_thin_wrapper_conversions.bats`:

```bash
@test "command-name is partial thin wrapper (<60 lines)" {
    local lines
    lines=$(wc -l < "$COMMANDS_DIR/command-name.md")
    [ "$lines" -lt 60 ]
}

@test "command-name has no raw SQL queries" {
    ! grep -qE "(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA|sqlite3)" "$COMMANDS_DIR/command-name.md"
}

@test "command-name uses ! prefix for preflight" {
    grep -qE "^!\[" "$COMMANDS_DIR/command-name.md"
}

@test "command-name has valid YAML frontmatter" {
    grep -q "^allowed-tools:" "$COMMANDS_DIR/command-name.md"
    grep -q "^description:" "$COMMANDS_DIR/command-name.md"
}

@test "command-name delegates to CLI command" {
    grep -q "python3 -m hooks.cli" "$COMMANDS_DIR/command-name.md"
}
```

**Test criteria for thin wrapper conversions:**
- File size under 60 lines
- No raw SQL queries (comprehensive keyword check)
- Uses `![ ]` preflight validation syntax
- Has `description` field in YAML frontmatter
- Delegates to appropriate CLI command

### Exclusions (Not Thin Wrappers)

Some commands intentionally remain as full orchestration commands and should NOT be converted to thin wrappers:

| Command | Reason | Lines |
|---------|--------|-------|
| `/epic-start` | Complex multi-agent orchestration, branch management, dependency tracking | ~250 |
| `/parallel-status` | Tmux session monitoring, worker health classification, SQL queries for blocked tasks | ~370 |

**Why these are excluded:**

1. **`/epic-start`**: Orchestrates parallel agent launches across an epic. Requires:
   - Git branch creation/management
   - Dependency graph analysis
   - Task tool for spawning multiple agents
   - Execution status file management
   - This is orchestration logic, not CLI delegation

2. **`/parallel-status`**: Real-time worker monitoring with:
   - Tmux pane output capture and classification
   - Worker health emoji mapping (🔄 working, 🚨 blocked, etc.)
   - Recovery state detection
   - Blocked dependency analysis
   - This logic is UI/display focused, not suitable for CLI

**Rule**: If a command uses the Task tool for agent spawning or requires real-time tmux interaction, it's an orchestration command, not a thin wrapper candidate.

### Migration Notes (Deprecated Commands)

Commands archived in `commands/archive/deprecated-thin-wrapper-conversion/`:

| Deprecated | Reason | Replacement |
|------------|--------|-------------|
| `/blocked` | Dashboard filter duplicate | `/dashboard` with filter |
| `/in-progress` | Dashboard filter duplicate | `/dashboard` with filter |
| `/validate` | Merged into preflight | `![ ]` preflight syntax |
| `/monitor-check` | Orphaned (monitor never built) | `/parallel-status` |
| `/monitor-start` | Orphaned (script doesn't exist) | N/A |
| `/monitor-stop` | Orphaned (depends on monitor) | N/A |

See `commands/archive/deprecated-thin-wrapper-conversion/README.md` for details.

## Common Gotchas

1. **ARGUMENTS parsing**: Use quotes for multi-word args
2. **Tool permissions**: Frontmatter must list required tools
3. **Path handling**: Use PROJECT_ROOT, not relative paths
4. **Exit codes**: Non-zero exits show as errors
5. **Output formatting**: Use markdown for structured output

## Directory Organization

```
commands/
├── archive/                # Deprecated commands
│   └── deprecated-thin-wrapper-conversion/
├── research/               # Research-related commands
├── *.md                    # Command files (no pm- prefix)
├── build.md                # Build automation
├── plan.md                 # Planning workflow
└── CLAUDE.md               # This file
```

## CLAUDE.md Placement Rules

| Directory Type | Documentation File | Why |
|----------------|-------------------|-----|
| Source dirs (`agents/`, `commands/`, `skills/`) | `CLAUDE.md` | Auto-loads when working here |
| Config dirs (`.claude/agents/`, `.claude/commands/`) | `README.md` | Ignored by parsers |

**Key distinction:**
- **Source directories** contain definitions symlinked globally → use `CLAUDE.md`
- **Config directories** (`.claude/*`) are project overrides → use `README.md` (or no docs)

## Security Improvements (Task #960)

Recent security hardening of FormalTask commands addresses Greptile code review findings:

### `/epic-decompose` Security Fixes
- **FK constraint fix**: Reordered DELETE statements to delete `acceptance_criteria` first (references tasks via foreign key)
- **SQL injection prevention**: Added proper escaping for task title field using `sed "s/'/''/g"`
- **Empty criteria validation**: Added validation to skip processing empty acceptance criteria

### `/task-add` Security Fixes
- **Portable grep replacement**: Replaced non-portable `grep -oP` with portable `sed` for BSD/macOS compatibility
- **Quote escaping**: Use base64 encoding for shell-to-Python data transport to safely handle quotes and special characters

These changes ensure robustness across different shells and operating systems while preventing SQL injection attacks.

## Related Documentation

- `hooks/cli/CLAUDE.md`: Python CLI implementations
- Root `CLAUDE.md`: FormalTask workflow overview
- `skills/CLAUDE.md`: Skills (contextual, not invoked)
