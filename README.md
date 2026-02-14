# FormalTask

Structured task management for AI-assisted development workflows. Integrates with Claude Code to provide epic-based planning, parallel task execution, and automated review workflows.

## Quick Start

```bash
pip install formaltask
```

After installation:

1. Set the required environment variable:
   ```bash
   export OPENROUTER_API_KEY="<your-key-here>"
   ```

2. Run the setup wizard:
   ```bash
   ft setup        # Interactive mode
   ft setup --yes  # Non-interactive (CI/scripts)
   ```

   The setup wizard initializes the database, registers Claude Code hooks, and verifies your configuration.

## Prerequisites

- **Python 3.11+** (required)
- **Git** (for hooks and version control)
- **tmux 3.2+** (optional, enables parallel worker features)

### Optional Feature Groups

Install additional features using pip extras:

| Extra | Purpose |
|-------|---------|
| `tui` | Terminal user interface dashboard |
| `test` | Testing dependencies (pytest, hypothesis) |
| `dev` | Development tools (ruff, basedpyright) |
| `agents` | Agent-related utilities |
| `dayflow` | HTTP client utilities |
| `mcp` | MCP server integration |
| `all` | All optional dependencies |

## Alternative Installation (Development)

For development or contributing to FormalTask:

```bash
git clone https://github.com/davidabeyer/formaltask.git
cd formaltask
python3 -m venv venv && source venv/bin/activate
./install.sh
```

### Manual pip Installation

Install in development mode:

```bash
pip install -e .
```

With optional dependencies:

```bash
pip install -e ".[all]"
```

Or install specific extras:

```bash
pip install -e ".[tui,test]"
```

### Git Hooks

The `./install.sh` script automatically configures git to use the project's tracked hooks. This enables:
- Pre-commit validation (linting, TDD guard)
- Pre-push task status enforcement
- Pre-merge-commit task validation

For manual installations, run: `git config core.hooksPath .githooks`

## Configuration

### Settings File

Claude Code settings are stored in `~/.claude/settings.json`. This file configures hooks, permissions, and other Claude Code behaviors.

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | Yes | LLM operations via OpenRouter |
| `PROJECT_ROOT` | For tests and CLI | Database path resolution |

### Database

Task data is stored in `.claude/formaltask.db` (SQLite).

## Usage

### Command Line

```bash
ft --help                      # Show available commands
ft work spawn <id>             # Spawn worker for a task
ft work list                   # List spawnable tasks
ft work watch                  # Monitor workers
ft work watch --spawn          # Monitor + auto-spawn ready tasks
ft work dashboard              # TUI dashboard
ft work inbox                  # Show blocked workers awaiting input
ft task list <epic>            # List tasks in an epic
ft task show <id>              # Show task details
ft task complete <id>          # Mark task as complete
ft task cancel <id>            # Cancel a task
ft epic list                   # List all epics
ft epic health <epic>          # Check epic health
ft setup                       # Run setup wizard
ft doctor                      # Verify configuration
```

Or run as a Python module:

```bash
python3 -m formaltask.cli --help
```

### Project Structure

```text
formaltask/
├── cli/                # CLI commands (ft <noun> <verb>)
├── core/               # Completion checking, config
├── data/               # Static data files
├── db/                 # Database connection, migrations
├── epics/              # Epic CRUD, YAML parsing
├── git/                # Worktree management, PR queries
├── hooks/              # Hook utilities (shared with hooks/)
├── llm/                # LLM integration (OpenRouter)
├── review/             # Review context, prompt building
├── skills/             # Skill metadata, span tracking
├── state/              # Findings, session tracking
├── tasks/              # Task lifecycle, dependencies, guards
├── validators/         # PreToolUse validators (TDD, doc-guard)
├── vault/              # Knowledge storage
├── workers/            # Worker spawning, monitoring
├── apps/               # TUI applications (dashboard)
└── utils/              # Shared utilities
agents/                 # Subagent definitions
hooks/                  # Hook entry points for Claude Code events
tests/                  # Test suite
.githooks/              # Tracked git hooks
.claude/
└── formaltask.db       # Task database (auto-created by ft setup)
```

See the [CLI Reference](docs/cli/index.md) for full command documentation, [Planning Workflow](skills/PLANNING-WORKFLOW.md) for the plan→critique→revise→decompose lifecycle, and [Architecture Overview](docs/architecture/overview.md) for how the pieces fit together.

### Dashboard

The interactive TUI dashboard (`ft work dashboard`) provides real-time monitoring and control of parallel workers.

![Dashboard](docs/assets/dashboard.png)

**Layout:** Status bar (top) showing task counts and auto-spawn state, task list (middle) with color-coded health indicators, terminal pane (bottom) showing the selected worker's output.

**Worker states:** Each task shows a health indicator — **LIVE** (running), **EXIT** (process ended), **HELP** (needs human input), **FIX** (has review findings), or **queued** (ready to spawn).

**Keybindings:**

| Key | Action |
|-----|--------|
| `j` / `k` | Navigate task list |
| `Enter` | Attach to selected worker (F12 to detach back) |
| `S` | Spawn next queued task |
| `A` | Toggle auto-spawn (automatically fills worker slots) |
| `+` / `-` | Adjust max worker limit (1-10) |
| `X` | Kill selected worker (double-tap to confirm) |
| `R` | Restart selected worker (double-tap to confirm) |
| `i` | Open inbox (blocked workers awaiting input) |
| `q` | Quit |

**Auto-spawn** fills available worker slots from the task queue. The status bar shows the current limit (e.g. `auto (5)`). Adjust with `+`/`-` to scale up or down without leaving the dashboard. This is the interactive equivalent of `ft work watch --spawn`.

## Development

### Running Tests

```bash
pytest tests/ --cov=formaltask
```

### Linting

```bash
ruff check formaltask/ --fix
ruff format formaltask/
```

### Type Checking

```bash
basedpyright formaltask/
```

## License

MIT License. See [LICENSE](LICENSE) for details.
