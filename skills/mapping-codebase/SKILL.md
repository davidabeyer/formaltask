---
name: mapping-codebase
description: Map codebase architecture - entry points, coupling, hotspots, call depth.
  Produces module docs, Mermaid diagrams, and answers interactive queries.
triggers:
- map codebase
- codebase architecture
- what are the entry points
- show me the coupling
- where are the hotspots
tools:
- mcp__auggie-mcp__codebase-retrieval
- mcp__morph-mcp__warpgrep_codebase_search
- Grep
- Glob
- Write
required_todos:
- discover
- analyze
- generate
---

<role>
WHO: Codebase cartographer
ATTITUDE: Map what exists. No speculation. Evidence from code.
</role>

<purpose>
Produce navigable maps of the codebase showing entry points, coupling, hotspots, and call depth.
</purpose>

<workflow>

## Phase 1: Discover

**quick:** Find entry points and modules with auggie. Report findings inline.

**full:** Enumerate the terrain systematically:

1. **Entry points** - Find all ways in:
   ```
   Glob: **/cli/**/*.py, **/commands/*.py  → CLI commands
   Grep: @app.route, @router → API endpoints
   Grep: def hook_, SessionStart, PreToolUse → Hooks
   ```

2. **Module boundaries** - Top-level packages:
   ```
   ls -d */ at project root
   ```

3. **Public interfaces** - Per module, find exports:
   ```
   Grep: ^class, ^def, __all__ in __init__.py
   ```

## Phase 2: Analyze

**quick:** Estimate complexity qualitatively (low/med/high). Skip full dimension scoring.

**full:** For each module, compute complexity dimensions:

| Dimension | How to measure |
|-----------|----------------|
| **Call depth** | warpgrep: trace from entry point to leaf |
| **Coupling** | Grep: `from X import`, `import X` across modules |
| **Hotspots** | Count: lines, functions, inbound references |
| **Entry points** | Count ways this module can be invoked |

**Complexity score** (1-10):
- 1-3: Single purpose, shallow calls, few dependencies
- 4-6: Multiple responsibilities, moderate depth
- 7-10: Deep chains, high coupling, many entry points

## Phase 3: Generate

**quick:** Present architecture summary inline with key entry points and coupling. Skip artifact files.

**full:** Generate full documentation artifacts.

**Invocation modes:**

| Flag | Output |
|------|--------|
| (none) | Full refresh: all docs + all diagrams |
| `--module X` | Deep-dive single module only |
| `--query "..."` | Answer one question, no artifacts |
| `--diagrams` | Regenerate Mermaid files only |

**Artifacts to produce:**

1. `.claude/codebase-map/{module}.md` per top-level package
2. `.claude/codebase-map/diagrams/entry-points.mmd`
3. `.claude/codebase-map/diagrams/coupling.mmd`
4. `.claude/codebase-map/diagrams/call-depth.mmd`

**Module doc template:**
```markdown
# {module}

## Purpose
{one sentence}

## Entry Points
{bulleted list with file:line}

## Public Interfaces
| Export | Type | Used by |
|--------|------|---------|

## Coupling
- imports: {list}
- imported by: {list}

## Hotspots
{top 3 files by complexity}

## Complexity: {N}/10
{one-line reason}
```

</workflow>

<rules>
- Use warpgrep for call chain tracing, not Grep
- Every claim needs file:line evidence
- Hotspots = files with most lines + most callers, not just big files
- Diagrams use Mermaid syntax
- Interactive queries (`--query`) don't modify artifacts
</rules>
