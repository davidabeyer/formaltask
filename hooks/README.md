# hooks/ - Detailed Documentation

Hook infrastructure for Claude Code automation. Event-driven workflows triggered by Claude Code lifecycle events.

## Directory Structure

```
hooks/
├── pretool/phases/         # PreToolUse validators (20 validators)
├── posttool/phases/        # PostToolUse handlers (step_logger, gmail_capture)
├── promptsubmit/phases/    # UserPromptSubmit hooks
├── session_start/          # SessionStart initialization
├── session_end/            # SessionEnd cleanup + phases/
├── stop/phases/            # SubagentStop enforcement
├── pre_compact/            # PreCompact handoff generation
├── subagent_start/         # SubagentStart hooks
├── post-commit/            # Post-commit validation
├── scripts/                # Utility scripts
├── tests/                  # Test suite
├── tui/                    # Terminal UI components
└── diagnostic/             # Diagnostic tools
```

## Commands

```bash
pytest hooks/tests/ -v --cov=hooks           # All tests with coverage
pytest hooks/tests/unit/test_X.py -v         # Specific test file
bats hooks/tests/  # BATS tests
```

## Hook Types

### Session Lifecycle
| Hook | Trigger | File |
|------|---------|------|
| SessionStart | Load task context in worktrees | `session_start/task_context_loader.py` |
| SessionStart | Auto-index codebase | `session_start/auto_index_codebase.py` |
| SessionStart | Delta handoff injection | `session_start/delta_handoff.py` |
| SessionEnd | Session ends | `session_end/runner.py` → `session_end/phases/` |
| UserPromptSubmit | User sends prompt | `promptsubmit/runner.py` → `promptsubmit/phases/` |
| PreCompact | Before /compact | `pre_compact/` |

### Task Context Loader (Worktree Agents)

The `task_context_loader.py` hook automatically injects task context when Claude starts in a worktree:

```
.task/
└── id              # Contains task ID (e.g., "42")
```

**How it works:**
1. Hook detects `.task/id` file in current directory
2. Reads task ID and queries formaltask.db
3. Extracts title, description, and PRP from `metadata.artifact_content`
4. Outputs JSON with `additionalContext` for Claude to receive

**Output format:**
```json
{
  "additionalContext": "# Task #42: Fix auth bug\n\n## PRP\n..."
}
```

**Why this exists:** Tmux worktree agents can't run `/pm-task-start` (slash commands don't work in tmux workers). This hook provides equivalent task context automatically at session start.

### Active Session Tracking

Session lifecycle is managed through phased runners in `session_start/` and `session_end/`:

- **SessionStart**: `session_start/runner.py` dispatches to phase modules (task context, indexing, delta handoff)
- **SessionEnd**: `session_end/runner.py` dispatches to `session_end/phases/` for cleanup

### Tool Validation (PreToolUse)

Validators live in `pretool/phases/`. Each is a standalone module loaded by `pretool/runner.py`.

| Validator | Purpose | File |
|-----------|---------|------|
| TDD Guard | Test-first enforcement | `pretool/phases/tdd_guard.py` |
| Doc Guard | Documentation update enforcement | `pretool/phases/doc_guard.py` |
| Git Safety | Dangerous git command blocking | `pretool/phases/git_safety.py` |
| Step Gate | Skill step ordering enforcement | `pretool/phases/step_gate.py` |
| Tool Redirect | WebSearch → semantic redirect | `pretool/phases/tool_redirect.py` |
| Grep Redirect | Grep → warpgrep suggestion | `pretool/phases/grep_redirect.py` |
| SQL Guard | SQL injection prevention | `pretool/phases/sql_guard.py` |
| Task Validator | Task state validation | `pretool/phases/task_validator.py` |
| Bash File Guard | Dangerous file operations | `pretool/phases/bash_file_guard.py` |
| Prompt Injection | Prompt injection detection | `pretool/phases/prompt_injection.py` |

#### Creating PreToolUse Validators

PreToolUse validators use plain functions with signature `check(ctx: dict) -> dict | None`:

```python
def check(ctx: dict) -> dict | None:
    """Validate tool call. Returns None to allow, dict to block."""
    tool_name = ctx.get("tool_name", "")
    if tool_name != "Bash":
        return None  # Allow non-Bash tools

    command = ctx.get("tool_input", {}).get("command", "")
    if "dangerous" in command:
        return {"decision": "block", "reason": "Blocked: dangerous pattern"}
    return None  # Allow
```

**Return values:**
- `None` - Permit tool call
- `{"decision": "block", "reason": str}` - Block with message
- `{"additionalContext": str}` - Allow with advisory context

### PostToolUse
| Hook | Trigger | File |
|------|---------|------|
| Step logger | After Read of skill step files | `posttool/phases/step_logger.py` |
| Gmail capture | After tool use | `posttool/phases/gmail_capture.py` |

## Skill Tracking & Step Enforcement

Span-based system that tracks every skill/step invocation and enforces correct step ordering. Inspired by OpenTelemetry's trace/span model.

### Architecture

```
USER INVOKES /plan
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ UserPromptSubmit: skill_run_initializer.py                          │
│   • Detects /skill-name invocation                                  │
│   • Reads SKILL.md frontmatter (uses_skill_run, required_todos)     │
│   • Extracts phases from ## Phase N: headers at runtime             │
│   • Writes skill_todos.json marker for TodoWrite validation         │
│   • Injects mode context (full vs quick)                            │
│   • Creates SkillRun output directory if uses_skill_run: true       │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼ Claude reads step files (steps/*.md)
        │
┌─────────────────────────────────────────────────────────────────────┐
│ PreToolUse: step_gate.py (ENFORCEMENT)                              │
│   • Intercepts Read of */skills/*/steps/*.md                        │
│   • Parses consumes/produces YAML frontmatter from ALL step files   │
│   • Queries skill_span.steps for visited steps in current span      │
│   • BLOCKS read if consumed artifacts not yet produced              │
│   • Respects optional: true (skippable without breaking chain)      │
│   • ROOT_INPUTS (e.g. "user-request") always satisfied              │
│   • Fail-open on errors                                             │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼ Read completes
        │
┌─────────────────────────────────────────────────────────────────────┐
│ PostToolUse: step_logger.py (TRACKING)                              │
│   • Intercepts Read of */skills/*/steps/*.md AND */SKILL.md         │
│   • 3-branch span algorithm:                                        │
│     1. Active span for skill? → append step                         │
│     2. Suspended root span? → resume                                │
│     3. Neither? → create new span (parent = current active span)    │
│   • Detects skill switches → suspends previous, emits events        │
│   • Writes to skill_span table + life_event table                   │
│   • Injects context: visit count warnings, ancestry ("from X")      │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼ Session ends
        │
┌─────────────────────────────────────────────────────────────────────┐
│ SessionEnd: close_active_skill_session()                            │
│   • Completes ALL active spans (prevents cross-session bleed)       │
│   • Emits session_end event for unclosed skill sessions             │
└─────────────────────────────────────────────────────────────────────┘
```

### Database

**skill_span** — one row per skill invocation instance (not per skill name):

| Column | Type | Purpose |
|--------|------|---------|
| `span_id` | TEXT PK | UUID prefix (12 chars) |
| `skill` | TEXT | Skill name (e.g. "plan") |
| `parent_span_id` | TEXT FK | NULL = user-invoked root. Non-NULL = composed child |
| `status` | TEXT | `active` / `suspended` / `completed` |
| `first_step` | TEXT | First step visited (or "SKILL" for monolithic) |
| `last_step` | TEXT | Most recent step |
| `steps` | TEXT | JSON array of all visited steps |
| `started_at` | TEXT | ISO timestamp |
| `suspended_at` | TEXT | When suspended (skill switch) |
| `completed_at` | TEXT | When completed (session end or terminal step) |

**life_event** — append-only ledger of all skill events:

| Column | Type | Purpose |
|--------|------|---------|
| `skill` | TEXT | Skill name |
| `phase` | TEXT | Step name or "SKILL" |
| `event_type` | TEXT | `step_enter` / `session_start` / `session_end` |
| `timestamp` | TEXT | ISO timestamp |

### Step File Frontmatter (consumes/produces DAG)

```yaml
---
consumes: [session-init]      # Artifacts this step needs
produces: [session-context]    # Artifacts this step provides
optional: true                 # If true, can be skipped without blocking dependents
---
```

The step_gate builds a dependency graph at runtime by parsing all step files in a skill's `steps/` directory. A step is blocked if any artifact it `consumes` hasn't been `produced` by a previously-visited step.

**ROOT_INPUTS** (always satisfied): `user-request`

### Span Composition (Parent Pointer)

The parent pointer is the composition signal — no flags needed:

```
plan (root, parent=NULL)
  └── critique (child, parent=plan's span_id)
       └── review (child, parent=critique's span_id)
```

When plan reads a critique step, the step_logger creates a child span with `parent_span_id` pointing to plan's active span. This is detected structurally, never configured.

### Skill Switches

When Claude reads a step from skill B while skill A is active:
1. step_logger emits `session_end` for skill A
2. Suspends skill A's span (`status='suspended'`)
3. Creates or resumes skill B's span
4. Emits `session_start` for skill B

### Debug Queries

```bash
# All open spans
sqlite3 "$DB_PATH" "SELECT span_id, skill, status, last_step FROM skill_span WHERE status != 'completed'"

# Span tree (nesting proof)
sqlite3 "$DB_PATH" "SELECT c.skill, c.status, p.skill as parent FROM skill_span c JOIN skill_span p ON c.parent_span_id = p.span_id"

# Step visit history for a skill
sqlite3 "$DB_PATH" "SELECT steps FROM skill_span WHERE skill='plan' AND status='active'"

# Recent step events
sqlite3 "$DB_PATH" "SELECT skill, phase, event_type, timestamp FROM life_event ORDER BY timestamp DESC LIMIT 20"
```

### Pre-Commit (`.git/hooks/pre-commit.legacy`)
| Check | Purpose | Mode |
|-------|---------|------|
| doc_guard | Requires CLAUDE.md updates for documented areas | Block/prompt |
| detect-secrets | Scans for hardcoded secrets | Block |
| pip-audit | Checks for vulnerable dependencies | Warn (on dep files only) |
| stub_check | Detects stub functions | Warn |
| api_stability | Checks for breaking API changes | Block |
| typescript_check | Runs tsc --noEmit on .ts files | Block |
| TDD Guard | Enforces test-first development | Block |

**Mode Variables:**
- `PRE_COMMIT_MODE=batch` - Accumulate all errors, report at end
- `FAIL_FAST=1` - Exit on first error

**BATS Tests:** `hooks/tests/test_pre_commit_hooks.bats`

#### Doc-Guard Architecture (Task #906)

The doc-guard system enforces documentation updates when code in documented areas changes.

**Implementation:**
| Module | Purpose |
|--------|---------|
| `pretool/phases/doc_guard.py` | PreToolUse validator — blocks commits without doc updates |
| `formaltask/validators/doc_guard.py` | Core doc-guard logic and configuration |

**CLI Commands:**
```bash
doc-guard pending    # Show pending documentation suggestions
doc-guard clear      # Clear pending suggestions after updates
doc-guard triggers   # List documented area patterns
doc-guard config threshold  # Get modification_threshold from config
```

**Configuration Flow:**
1. `.doc-guard.yaml` defines documented areas and settings
2. `doc_guard_config.py` loads config via `load_config()`
3. Legacy bash script calls `get_modification_threshold()` which invokes Python
4. Threshold from YAML is used instead of deprecated bash constant

**Migration from Bash Constant:**
- **Before**: `DOC_MODIFICATION_THRESHOLD="${DOC_MODIFICATION_THRESHOLD:-20}"` in bash
- **After**: `get_modification_threshold()` bash function calls Python CLI
- **Benefit**: Single source of truth in `.doc-guard.yaml`

## Pre-Commit Hooks (.pre-commit-config.yaml)

This project uses pre-commit hooks for code quality. Hooks execute in YAML definition order.

### Hook Execution Order

| Order | Hook | Purpose |
|-------|------|---------|
| 1 | ruff | Linting (auto-fix enabled) |
| 2 | ruff-format | Code formatting |
| 3 | trailing-whitespace | Whitespace cleanup |
| 4 | end-of-file-fixer | Ensure newline at EOF |
| 5 | check-yaml | YAML syntax validation |
| 6 | check-added-large-files | Block files >500KB |
| 7 | check-merge-conflict | Detect merge conflict markers |
| 8 | debug-statements | Detect leftover debugger calls |
| 9 | basedpyright | Type checking (requires Node.js 20+) |
| 10 | semgrep | Security scanning (SAST) |

### Escape Hatches

When you need to suppress a specific finding, use these verified escape hatch patterns:

#### Pyright Type Errors

```python
# Suppress all type errors on a line
x: int = "string"  # type: ignore

# Suppress specific error type
y: str = 123  # type: ignore[assignment]
```

**Note:** basedpyright requires Node.js 20+ installed. Uses baseline file at `baselines/pyright-baseline.json` for gradual adoption.

#### Ruff Complexity (C901)

```python
def complex_function(a, b, c, d, e):  # noqa: C901
    """Function with intentionally high complexity."""
    if a: return 1
    if b: return 2
    # ... many branches ...
```

**Note:** Max complexity is 10 (configured in `pyproject.toml`). Use sparingly.

#### Semgrep Security Findings

```python
# Suppress all semgrep findings on a line
eval(user_input)  # nosemgrep

# Suppress specific rule
exec(code)  # nosemgrep: python.lang.security.audit.exec-detected
```

**Note:** Semgrep scans `hooks/` directory only. Uses `--config auto` for rule detection.

### Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `basedpyright: command not found` | Node.js not installed | Install Node.js 20+ |
| `could not baseline diagnostics` | File outside project root | Run from project root |
| `semgrep timeout` | Large scan | Increase `SEMGREP_TIMEOUT` env var |
| Type errors in new file | Not in baseline | Add `# type: ignore` or fix types |
| C901 complexity error | Function too complex | Refactor or add `# noqa: C901` |

### Test Coverage

Escape hatches are verified in `hooks/tests/integration/test_escape_hatches.py`:
- `test_pyright_type_ignore_*` - Verifies type: ignore syntax
- `test_ruff_noqa_c901_*` - Verifies noqa: C901 syntax
- `test_semgrep_nosemgrep_*` - Verifies nosemgrep syntax
- `test_hook_order_matches_yaml_definition` - Verifies execution order

## Testing Requirements

- **Coverage**: >80% for hook phase modules
- **TDD**: Red-Green-Refactor (load `tdd-workflow` skill)
- **Mocking**: All external deps (MCP, GitHub CLI, file system)
- **Fixtures**: See `tests/conftest.py`
- **Test Location**: All tests in `hooks/tests/`, NOT in source dirs like `session_end/`

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `PROJECT_ROOT` | For tests | Database path resolution |
| `USE_LEGACY_SESSION_END` | No | Set to 1/true/yes to use monolithic session_end_worker.py (default: decomposed modules) |

## Intentional Code Patterns

### Dual Import Pattern

Hook scripts use try/except imports to support both direct execution and module invocation:

```python
try:
    from formaltask.db.connection import DatabaseConnection
except ModuleNotFoundError:
    from db_connection import DatabaseConnection
```

**Why**: Hook scripts may run as standalone scripts (direct execution) or as part of the `formaltask` package (pytest, module imports). The dual import pattern handles both cases.

**Where used**: Hook phase modules in `pretool/`, `posttool/`, `session_start/`, `session_end/`, `pre_compact/`

### Public API Exports Pattern (Task #1866)

All hooks modules now define explicit public APIs via type-annotated `__all__` exports:

```python
# formaltask/tasks/guards.py
__all__: list[str] = [
    "ReviewGuard", "AcceptanceCriteriaGuard"
]
```

**Benefits**:
- **IDE Support**: Better autocomplete and static analysis
- **API Clarity**: Clear boundaries between public interfaces and internals
- **Type Safety**: `list[str]` annotation enables better tooling support

### Exclusive Transactions Pattern

For race-condition-sensitive operations, use `exclusive=True`:

```python
with DatabaseConnection(db_path, exclusive=True) as conn:
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
    # Transaction auto-commits on success, auto-rollbacks on exception
```

**Why**: EXCLUSIVE mode prevents concurrent reads/writes. The context manager handles commit on success and rollback on exception.

**Where used**: `formaltask/tasks/` (state transitions)

**When to use**:
- Multi-step updates that must be atomic
- Race conditions between parallel workers
- State transitions that shouldn't be partially applied

### Defensive Dict Access Pattern

Session data may have malformed or wrong-type values. Always validate before chained `.get()`:

```python
# Good: Type check before chaining
frontmatter = session_data.get("frontmatter", {})
if not isinstance(frontmatter, dict):
    frontmatter = {}
last_line = int(frontmatter.get("last_summary_line", 0))

# Bad: Crashes if frontmatter is string
last_line = int(session_data.get("frontmatter", {}).get("last_summary_line", 0))
```

**Where used**: Session data parsing modules

### Regex Escape Pattern (Security)

When using user-controlled or file-sourced data in regex patterns, always escape to prevent regex injection:

```python
# Good: Escape user-controlled keys before regex use
escaped_key = re.escape(key)
pattern = rf"^{escaped_key}:.*$"
content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

# Bad: Regex metacharacters interpreted as patterns
pattern = rf"^{key}:.*$"  # key="price." matches "price" + any char
```

**Why**: Frontmatter keys or user input may contain regex metacharacters (`.`, `*`, `+`, `[`, `]`, `^`, `$`). Without escaping, these are interpreted as regex patterns, potentially matching unintended content or causing ReDoS.

**Where used**: Session processing modules

### Boolean Environment Variable Pattern

Environment variables should accept common boolean string representations:

```python
def is_cognee_enabled() -> bool:
    """Check if Cognee storage is enabled via environment variable."""
    value = os.getenv("COGNEE_STORAGE_ENABLED", "true").lower().strip()
    return value in ("true", "1", "yes")
```

**Why**: Users may set environment variables as `1`, `yes`, `true`, `True`, etc. Only checking for exact `"true"` excludes common alternatives.

**Where used**: Environment configuration modules

### Robust Path Extraction Pattern

When extracting metadata from file paths, use marker-based lookup instead of fixed indices:

```python
# Good: Find marker and extract relative to it
topic = "unknown"
if "sessions" in parts:
    sessions_idx = parts.index("sessions")
    if sessions_idx + 1 < len(parts):
        topic = parts[sessions_idx + 1]

# Bad: Hardcoded index fails on short/different paths
topic = parts[-5]  # Raises IndexError if path has < 5 parts
```

**Why**: Paths may vary in depth depending on configuration or execution context. Fixed indices like `parts[-5]` fail on short paths or different structures.

**Where used**: Session processing modules

### URL Filtering Pattern

When extracting file paths from text, filter out URLs that may match file patterns:

```python
# Extract file paths but filter out URLs
raw_files = re.findall(r"^-?\s*(.+\.[\w]+)\s*$", files_section, re.MULTILINE)
files = [f for f in raw_files if not f.startswith(("http://", "https://"))]
```

**Why**: URLs ending in `.extension` (e.g., `https://github.com/repo/file.py`) match simple file regex patterns but aren't local file paths.

**Where used**: Session processing modules

### Timestamp Coordination Pattern (Handoff Generation)

When generating handoff files in two phases (placeholder → real), coordinate timestamps to ensure overwrite:

```python
# Good: Capture timestamp at placeholder creation, reuse for real handoff
placeholder_timestamp = datetime.now()
placeholder = HandoffContext(timestamp=placeholder_timestamp, ...)
save_handoff(worktree, session_id, placeholder)  # Creates 2025-12-09T10-30-00.md

# ... API call (60-100 seconds) ...

# CRITICAL: Override API response timestamp with placeholder timestamp
handoff.timestamp = placeholder_timestamp  # Same timestamp = same filename
save_handoff(worktree, session_id, handoff)  # OVERWRITES placeholder file

# Bad: Use API response timestamp (different = orphaned placeholder)
# handoff.timestamp = gemini_response.timestamp  # Different timestamp!
# save_handoff(worktree, session_id, handoff)  # Creates NEW file, placeholder orphaned
```

**Why**: Placeholder uses `datetime.now()` (local time), but Gemini returns UTC timestamps. Even with same timezone, sub-second timing differences cause different filenames. Using the same datetime object ensures identical filenames.

**Where used**: `pre_compact/` handoff generation

**Test coverage**: `test_write_placeholder_handoff_returns_timestamp`, `test_main_uses_placeholder_timestamp_for_real_handoff`

### Modular Decomposition Pattern (Task #1862)

When decomposing large monolithic modules, create focused modules with single responsibilities:

```python
# session_end/__init__.py - Clean module exports
from hooks.session_end.cognee_integration import CogneeClient, CogneeError
from hooks.session_end.file_writer import FileWriterError, HandoffWriter
from hooks.session_end.llm_client import LLMClient, LLMError
from hooks.session_end.session_metadata import MetadataError, SessionMetadata

__all__ = [
    "CogneeClient", "CogneeError", "HandoffWriter",
    "LLMClient", "LLMError", "SessionMetadata"
]
```

**Key principles:**
- **Single Responsibility**: Each module handles one concern (metadata, file I/O, LLM calls)
- **Dataclass Models**: Use dataclasses for structured data (`SessionMetadata`)
- **Specific Exceptions**: Define module-specific error types (`FileWriterError`, `LLMError`)
- **Atomic Operations**: Use temp+rename patterns for file safety
- **Clean Exports**: Re-export all symbols in `__init__.py` for easy imports
- **Feature Flags**: Use environment variables for rollback capability

**Architecture benefits:**
- Individual modules testable in isolation
- Clear separation of concerns
- Easier debugging and maintenance
- Gradual migration with feature flags

**Where used**: Hook phase modules

### Atomic File Operations Pattern (Task #1862)

For safe file writes, use temp file + atomic rename to prevent corruption:

```python
# session_end/file_writer.py - Atomic write implementation
class HandoffWriter:
    def write(self, path: Path, content: str) -> None:
        """Atomic write with temp file + rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        # Use temp file + atomic rename pattern
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)  # Atomic on POSIX systems
```

**Key benefits:**
- **Atomic Operation**: Either complete file or no file (no partial writes)
- **Race Condition Safe**: Other processes see either old or new content
- **Symlink Support**: Special handling for atomic symlink updates

**Symlink atomic update pattern:**
```python
def update_symlink(self, path: Path, target: Path) -> None:
    """Update symlink atomically using temp symlink + rename."""
    temp_path = path.with_suffix(".tmp")
    if temp_path.is_symlink() or temp_path.exists():
        temp_path.unlink()
    temp_path.symlink_to(target)
    os.rename(str(temp_path), str(path))  # Atomic rename
```

**Where used**: File writing utilities

### LLM Client Wrapper Pattern (Task #1862)

Wrap external LLM APIs with consistent error handling and lazy initialization:

```python
# session_end/llm_client.py - LLM API integration
class LLMClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._client: OpenAI | None = None  # Lazy initialization

    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client (lazy initialization)."""
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=BASE_URL)
        return self._client

    def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate completion. Raises LLMError on failure."""
        try:
            client = self._get_client()
            response = client.chat.completions.create(...)
            return response.choices[0].message.content or ""
        except (APITimeoutError, APIConnectionError, RateLimitError,
                AuthenticationError, BadRequestError) as e:
            raise LLMError(f"API error: {e}") from e
```

**Key benefits:**
- **Lazy Initialization**: Client created only when needed
- **Specific Exception Handling**: Catch OpenAI-specific exceptions
- **Consistent Interface**: Standardized error types across modules
- **Null Safety**: Handle None content responses

**Where used**: LLM integration modules

## Review System

Multi-round code review system with deterministic finding IDs and progress tracking.

### Storage Structure

```
epic-reviews/
├── {epic}/
│   ├── findings.json     # Single source of truth for all findings
│   ├── progress.json     # Round-by-round metrics
│   └── round-N.md        # Narrative reports per round
├── task/
│   └── {id}.json         # Task-level reviews
└── adhoc/
    └── {scope-slug}.json # Ad-hoc security/perf reviews
```

### Commands

```bash
# Run a review (triggers agent, saves findings)
/review epic:auth-system
/review task:42
/review security:payment-module

# Query findings
/review list epic:auth-system              # All findings
/review list epic:auth-system --status open
/review list epic:auth-system --severity P0

# Update finding status
/review mark abc12345 --fixed --task 99
/review mark def67890 --wontfix --reason "By design"

# View progress history
/review progress epic:auth-system
```

### Finding Lifecycle

| Status | Description |
|--------|-------------|
| `open` | Not yet addressed |
| `fixed` | Resolved (includes `fixed_by_task` ID) |
| `wontfix` | Acknowledged, not fixing (includes `reason`) |

### Migration from Old Commands

| Old Command | New Command |
|-------------|-------------|
| `/pm-review-fix epic` | `/review epic:epic` |
| `/pm-review-status task` | `/review list task:id` |
| `/pm-review-add epic type title` | `/review epic:epic` |
| `/pm-review-skip task` | Direct DB update (emergency only) |

**Note**: Old `/pm-review-*` commands are deprecated and will be removed.

### Implementation

- Gate enforcement: `formaltask/tasks/guards.py` blocks completion until reviews pass
- Note: Legacy `review_store.py` and `review.py` were removed as dead code (superseded by Greptile async review via `/pm-pr-create`)

## Common Gotchas

1. **Hook not firing**: Check `~/.claude/settings.json` not `~/.claude.json`
2. **Import errors**: Ensure `PROJECT_ROOT` is set for tests
3. **Permission denied**: Make hook scripts executable (`chmod +x`)
4. **Timeout**: Default is 5s, increase for complex operations
5. **TDD Guard files**: `.claude/tdd-guard/data/*.json` files are gitignored (ephemeral runtime state). Only `instructions.md` and `ignore-patterns.txt` are tracked.

## State File Protocol (Task #1476)

The state file protocol enables efficient worker state monitoring by writing JSON state files from tmux status bar hooks, replacing expensive pane scraping on the hot path.

### Architecture Overview

```
┌─────────────────────┐     ┌──────────────────────────────────┐
│  tmux status-left   │────▶│ ~/.cache/tmux-claude-status/     │
│  (writes state)     │     │   42-state.json                  │
└─────────────────────┘     └──────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────┐     ┌──────────────────────────────────┐
│  Orchestrator API   │◀────│  read_worker_state(task_id)      │
│  get_summary()      │     │  - staleness detection (30s)     │
└─────────────────────┘     │  - fallback to pane scrape       │
                            └──────────────────────────────────┘
```

### State File Location

```
~/.cache/tmux-claude-status/{task_id}-state.json   # Primary path
~/.cache/tmux-claude-status/task-{task_id}-state.json  # Fallback path
```

### Schema v1 Format

```json
{
  "schema_version": "1",
  "task_id": "42",
  "session_name": "task-42",
  "phase": "working",
  "ts": "2025-12-23T07:30:00Z",
  "tool": "Read",
  "last_line": "Processing file.py...",
  "exit_code": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Always "1" for v1 format |
| `task_id` | string | Yes | Task identifier |
| `session_name` | string | Yes | tmux session name (e.g., "task-42") |
| `phase` | string | Yes | Worker state: working, ready, blocked, error, exited |
| `ts` | string | Yes | ISO 8601 timestamp for staleness detection |
| `tool` | string | No | Current tool being executed |
| `last_line` | string | No | Last line of output (for question detection) |
| `exit_code` | int/null | No | Exit code if worker has exited |

### Staleness Detection

State files are considered **stale** after 30 seconds (configurable via `STALENESS_THRESHOLD_SECONDS`):

- **Fresh** (`is_stale=False`): State file < 30 seconds old → use state file data
- **Stale** (`is_stale=True`): State file >= 30 seconds old → fallback to pane scrape

### Fallback Behavior

When state file is missing, stale, or corrupt, the system falls back to pane scraping:

```python
def get_worker_state(session_name, task_id):
    state = read_worker_state(task_id)
    if state and not state.get('is_stale'):
        return state  # Hot path: use state file
    # Fallback: capture tmux pane output
    output = capture_pane(session_name)
    return classify_output(output)
```

### Fallback Monitoring (Task #1477)

The system tracks fallback usage to detect hook issues:

| Counter | Description |
|---------|-------------|
| `FALLBACK_COUNT` | Number of times pane scrape fallback used |
| `TOTAL_CALLS` | Total `get_worker_state_dict()` calls |

**Logging:**
- Every 100 fallbacks: `"Fallback to pane scrape used N times"`
- When fallback rate > 20% (after 100+ calls): Warning logged

**Alert Threshold:** If fallback rate exceeds 20%, indicates hook issues (state files not being written properly).

### Integration Points

| Module | Function | Purpose |
|--------|----------|---------|
| `worker_health_analyzer.py` | `read_worker_state()` | Read/parse state files with staleness |
| `worker_health_analyzer.py` | `get_worker_state_dict()` | Complete worker state with monitoring |

### Deprecated: .status String Files

Old `.status` files containing simple string status are deprecated. Migrate to JSON state files for:
- Structured data with multiple fields
- Staleness detection via timestamp
- Consistent parsing with `read_worker_state()`

## Advanced Patterns

For detailed implementation patterns, load the `hooks-reference` skill:

```
Skill(hooks-reference)
```

Covers: background workers, database transactions, file locking, stub detection, doc-guard, Cognee, parallel workers.

## Phase Integration Guidelines

When implementing multi-phase features (like tmux-orchestrator-enhancements), phases naturally build on each other:

### Integration vs Modification

- **Phase Integration**: Later phases USE earlier phase components (correct)
  - Phase 2 status reads Phase 1's state files for display

- **Phase Modification**: Changing Phase 1 code during Phase 3 work (requires justification)
  - Valid: PRP explicitly called for cross-phase changes
  - Invalid: Ad-hoc changes without PRP specification

### When Cross-Phase Changes Are Expected

1. **Integration Tasks**: Any task labeled "integration" in the PRP may touch all phases
2. **Bug Fixes**: Fixing a bug discovered in Phase 1 during Phase 3 is acceptable
3. **Refactoring**: Consolidating duplicated code across phases (document in commit)

### Documentation Requirements

When modifying prior phase code:
1. Note the change in commit message
2. Reference the PRP section that authorized it
3. Update phase documentation if behavior changes

See also: `CLAUDE.md` > "Phase Integration Patterns" for data coordination details.

---

## Code Style: SIM117 Compliance (Dec 2025)

Test files in `hooks/` use Python 3.10+ parenthesized context manager syntax per ruff SIM117:

```python
# Preferred style (SIM117 compliant)
with (
    patch('module.function') as mock_fn,
    patch('module.other') as mock_other,
):
    test_code()
```

---

## Error Handling Style Guide (Task #1853)

All exception handlers must be visible through logging. Zero tolerance for silent failures.

### Log Levels by Category

| Category | Level | Criteria |
|----------|-------|----------|
| Critical | ERROR | Data loss risk, unrecoverable |
| Warning | WARNING | User visible, degraded experience |
| Debug | DEBUG | Expected failures, internal fallbacks |

### Patterns

```python
import logging
logger = logging.getLogger(__name__)

# GOOD: Logged exception with context
try:
    parse_json(text)
except json.JSONDecodeError as e:
    logger.debug("JSON parse failed, using fallback: %s", e)
    return fallback_value

# GOOD: User-facing CLI error
try:
    validate_task_id(task_id)
except ValueError as e:
    print(f"Invalid task ID: {e}")
    sys.exit(65)  # EX_DATAERR

# BAD: Swallowed exception
try:
    risky_operation()
except SomeError:
    pass  # Silent failure - debugging impossible!
```

### Exception Categories

1. **Use specific types** - Never `except Exception:` without justification
2. **Capture exception** - Always `except X as e:` for logging
3. **Include context** - Log what failed and why
4. **Re-raise when appropriate** - Don't swallow unrecoverable errors

### UI Framework Exceptions

For Textual's `NoMatches` exception (widget not found):

```python
try:
    widget = self.query_one("#my-widget", MyWidget)
except NoMatches:
    pass  # Widget not mounted yet (expected during startup)
```

This is acceptable because:
- It's an expected condition during app initialization
- The comment explains why it's safe to ignore
- Using specific `NoMatches` type (not broad `Exception`)

### Audit Reference

See `hooks/CLAUDE.md` for error handling patterns.

---

See also: `formaltask/validators/CLAUDE.md`, `formaltask/db/migrations/CLAUDE.md`
