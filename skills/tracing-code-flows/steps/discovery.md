---
consumes: [trace-config]
produces: [entry-points]
---
# Phase 1: Discovery

## Quick Mode

Enumerate entry points inline. Report 3-5 key paths without formal inventory.

## Full Mode (Standard / Deep)

### Step 1: Identify Scope

Determine which directories and files are in scope vs out of scope for the trace.

### Step 2: Enumerate ALL Entry Points

Find every entry point, not just the obvious ones.

| Entry Point Type | Examples |
|------------------|----------|
| CLI commands | Commands, flags, subcommands |
| API endpoints | REST, GraphQL, RPC |
| Event handlers | Hooks, callbacks, webhooks |
| Scheduled jobs | Cron, timers |
| Exports | Public functions, SDK methods |

### Step 3: Map Dependencies

For each entry point, identify external dependencies:
- Database queries
- API calls
- File system access
- Environment variables

### Output

N entry points, each with:
- **name** - human-readable identifier
- **type** - from the table above
- **file:line** - exact source location
- **signature** - function/method signature
