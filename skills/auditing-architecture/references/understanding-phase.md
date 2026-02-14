# Understanding Phase Protocol

Before any evaluation, build genuine comprehension of the codebase.

## Why This Matters

Surface-level pattern matching produces false positives:
- A function named `parse_and_validate` might be perfectly cohesive
- Deep nesting might be unavoidable given the problem domain
- "Unused" code might be called via dynamic dispatch

**Understanding first prevents embarrassing incorrect findings.**

---

## Architecture Mapping Steps

### Step 1: Identify Module Boundaries

```python
# Find all top-level directories with code
Glob("**/__init__.py")  # Python
Glob("**/index.{ts,js}")  # TypeScript/JS
Glob("**/mod.rs")  # Rust

# Read each module's docstring/README
for module in modules:
    Read(f"{module}/__init__.py")  # Check module docstring
    Read(f"{module}/README.md")  # If exists
```

**Document:**
- Module names and locations
- Stated purpose (from docs/docstrings)
- Apparent purpose (from code inspection)

### Step 2: Map Data Flow

```python
# Find data model definitions
mcp__auggie-mcp__codebase-retrieval(
    "Find data models, schemas, database tables, type definitions"
)

# Find where data enters the system
mcp__morph-mcp__warpgrep_codebase_search(
    "Find API endpoints, CLI handlers, input parsing",
    repo_path=target_path
)

# Find where data exits the system
mcp__morph-mcp__warpgrep_codebase_search(
    "Find output writers, API responses, file exports",
    repo_path=target_path
)
```

**Document:**
- Core data structures
- Input sources
- Output destinations
- Transformation pipeline

### Step 3: Identify Key Abstractions

```python
# Find base classes, protocols, interfaces
Grep(pattern="class.*\\(ABC\\)|class.*\\(Protocol\\)|interface\\s+\\w+")

# Find factories, builders, registries
Grep(pattern="Factory|Builder|Registry|Provider")

# For each: count implementations
for abstraction in abstractions:
    Grep(pattern=f"class.*\\({abstraction}\\)")
```

**Document:**
- Abstractions and their purpose
- Number of implementations
- Whether abstraction is justified

### Step 4: Trace Representative Paths

Select 3-5 execution paths that represent core functionality.

**For each path:**
1. Start at entry point (CLI command, API endpoint, event handler)
2. Follow calls through each layer
3. Note data transformations
4. Document the full journey

```python
# Example: Trace a CLI command
# 1. Find entry point
Read("cli/main.py")  # Look for command registration

# 2. Follow to handler
Read("handlers/process.py")  # Find the command handler

# 3. Trace through business logic
Read("services/processor.py")  # Business logic

# 4. Follow to data layer
Read("repositories/data.py")  # Data access

# Document the chain with actual code references
```

---

## Comprehension Checkpoint

Before proceeding to evaluation, answer these questions:

1. **Purpose:** What problem does this codebase solve?
2. **Mechanism:** How does it solve it? (high-level)
3. **Boundaries:** What are the module responsibilities?
4. **Flow:** How does data move through the system?
5. **Patterns:** What architectural patterns are used and why?

**If you cannot answer all five, continue understanding. Do not evaluate.**

---

## Working File Format

Write understanding to: `{working_dir}/architecture.md`

```markdown
# Architecture Understanding

## Purpose
{What this codebase exists to do}

## Module Map

| Module | Responsibility | Key Files |
|--------|---------------|-----------|
| {name} | {purpose} | {files} |

## Data Flow

```
Input: {sources}
   ↓
Processing: {transformation steps}
   ↓
Output: {destinations}
```

## Key Abstractions

| Abstraction | Purpose | Implementations | Justified? |
|-------------|---------|-----------------|------------|
| {name} | {why} | {count} | {yes/no + reason} |

## Traced Paths

### Path 1: {name}
{entry_point} → {step1} → {step2} → {output}

**What I learned:** {insight}

## Open Questions
{Things still unclear - may need to investigate during analysis}
```

---

## Common Understanding Failures

| Failure | Consequence | Prevention |
|---------|-------------|------------|
| Skipped to findings | False positives | Complete comprehension checkpoint |
| Only read grep matches | Missed context | Read full files |
| Assumed purpose | Criticized correct code | Verify with docs/comments/git |
| Ignored dynamic behavior | Missed callers | Check for reflection/dispatch |
