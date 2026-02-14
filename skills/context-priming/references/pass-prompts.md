# Pass Prompts

Four sequential passes. Each builds on previous. Run in order.

---

## Common Preamble (all passes)

```
AUDIT PASS: {PASS_NAME}

WORKING DIR: {working_dir}

INPUT:
- Code Index: {working_dir}/01-code-index.md (READ THIS FIRST - actual code)
- Previous Passes: {working_dir}/02-*.md (if any)

OUTPUT: {working_dir}/02-{pass_name}.md

PHILOSOPHY: antirez + Go creators
- Delete before abstract
- Direct over indirect
- Concrete over generic
- Prose over puzzles

TOOLS AVAILABLE:
- mcp__auggie-mcp__codebase-retrieval (semantic search)
- mcp__morph-mcp__warpgrep_codebase_search (pattern tracing)
- Read (full file inspection - USE LIBERALLY)
- Grep (find patterns)

ITERATIVE DEEPENING: If you need more context, READ MORE CODE.
Don't guess. Don't assume. Read the actual source.

---
```

---

## Pass 1: Structure

```
{PREAMBLE with pass_name="structure"}

QUESTION: How does this code fit the system?

You are mapping the skeleton. Not judging yet - understanding.

TASKS:

1. ENTRY POINTS
   - How does execution enter this module?
   - CLI commands? API endpoints? Other modules calling in?
   - For each: trace the full path through the code

2. CALL CHAINS
   - What's the typical call depth?
   - Where do chains converge (shared helpers)?
   - Where do chains diverge (branches)?

3. MODULE BOUNDARIES
   - What's public vs internal?
   - Are boundaries clear or porous?
   - What would break if this module changed?

4. DEPENDENCIES
   - What does this module depend on?
   - What depends on this module?
   - Circular dependencies?

FINDINGS FORMAT:

```markdown
# Structure Pass: {target}

## Entry Points

### 1. {entry_point_name}
**How reached:** {CLI/API/import}
**Full trace:**
```
{entry}
  → {step1} ({file}:{line})
  → {step2} ({file}:{line})
  → {result}
```
**Files touched:** {list}
**Depth:** {N levels}

## Call Graph Analysis

**Convergence points (shared helpers):**
- `{function}` called by {N} different paths

**Divergence points (branches):**
- `{function}` branches to {N} different outcomes

## Module Boundaries

**Public interface:**
- `{function}` - {purpose}

**Internal (should be private):**
- `{function}` - {why internal}

**Unclear:**
- `{function}` - {why unclear}

## Dependencies

**This module depends on:**
| Dependency | Used For | Coupling |
|------------|----------|----------|
| {module} | {purpose} | tight/loose |

**Depends on this module:**
| Dependent | Uses | Would break if |
|-----------|------|----------------|
| {module} | {what} | {change} |

## Questions for Data Pass

- {specific question about data flow discovered here}
```

---

## Pass 2: Data

```
{PREAMBLE with pass_name="data"}

PREVIOUS: Read {working_dir}/02-structure.md first.

QUESTION: Where does data live and how does it flow?

You are tracing data through the skeleton. Following values, not control flow.

TASKS:

1. STATE INVENTORY
   - Where is state stored? (instance vars, globals, closures, DB)
   - For each: who owns it? who mutates it?

2. DATA ENTRY POINTS
   - Where does data enter the system?
   - User input? Files? Network? Other modules?

3. TRANSFORMATION CHAINS
   - Pick 3 key data types
   - Trace: entry → transformations → exit
   - Note every mutation along the way

4. OWNERSHIP CLARITY
   - For mutable state: is ownership clear?
   - Can you answer "who's allowed to change this?"

FINDINGS FORMAT:

```markdown
# Data Pass: {target}

## State Inventory

### {state_name}
**Type:** {class attribute / global / closure / DB}
**Location:** `{file}:{line}`
**Owner:** {who creates/destroys it}
**Mutators:** {who changes it}
```python
# Actual code showing the state
{code}
```
**Clarity:** Clear / Unclear / Dangerous
**Why:** {explanation}

## Data Flow: {data_type_1}

```
ENTRY: {source}
  ↓
{transformation 1} @ {file}:{line}
  mutates: {what changes}
  ↓
{transformation 2} @ {file}:{line}
  mutates: {what changes}
  ↓
EXIT: {destination}
```

**Observations:**
- {observation about this flow}

## Ownership Analysis

| State | Owner | Mutators | Clear? |
|-------|-------|----------|--------|
| {name} | {who} | {list} | yes/no |

**Unclear ownership (potential bugs):**
- `{state}`: {why unclear}

## Questions for Complexity Pass

- {specific question about complexity discovered here}
```

---

## Pass 3: Complexity

```
{PREAMBLE with pass_name="complexity"}

PREVIOUS: Read {working_dir}/02-structure.md and {working_dir}/02-data.md first.

QUESTION: What's genuinely complex vs accidentally complex?

You are distinguishing essential complexity (domain-inherent) from accidental
complexity (our fault). Only accidental complexity is a finding.

TASKS:

1. COGNITIVE LOAD HOTSPOTS
   - Which functions take longest to understand?
   - Measure: time to explain to a colleague
   - >2 minutes = hotspot

2. MIXED CONCERNS
   - Which functions do multiple unrelated things?
   - I/O + validation + transform + persist = mixed
   - Orchestration (calling others) is fine

3. NESTING DEPTH
   - Where is nesting deepest?
   - >3 levels = investigate
   - Is depth from domain complexity or poor structure?

4. CLEVER CODE
   - Where would a reader say "wait, what?"
   - One-liners that need comments = too clever
   - Idioms only experts know = context-dependent

ESSENTIAL VS ACCIDENTAL:

| Type | Example | Action |
|------|---------|--------|
| Essential | State machine with 10 states (domain has 10 states) | Document, don't simplify |
| Accidental | 10 nested ifs that could be a lookup table | Finding |
| Unclear | Complex validation (is domain complex?) | Investigate |

FINDINGS FORMAT:

```markdown
# Complexity Pass: {target}

## Cognitive Load Hotspots

### 1. `{function_name}` @ {file}:{line}
**Time to understand:** {estimate}
**Why hard:**
- {reason 1}
- {reason 2}

```python
{the problematic code}
```

**Essential or Accidental:** {verdict}
**Evidence:** {why you classified it this way}
**If Accidental - Simplification:**
```python
{how it could be simpler}
```

## Mixed Concerns

### `{function_name}` @ {file}:{line}
**Concerns found:**
1. {concern 1} (lines X-Y)
2. {concern 2} (lines X-Y)
3. {concern 3} (lines X-Y)

```python
{code with concerns annotated}
```

**Verdict:** Mixed (accidental) / Orchestration (fine)
**Evidence:** {why}

## Deep Nesting

### `{function_name}` @ {file}:{line}
**Depth:** {N levels}
**Structure:**
```
if ...
  if ...
    for ...
      if ...  ← 4 levels
```

**Verdict:** Domain complexity / Poor structure
**If Poor Structure - Refactor:**
{how to flatten}

## Clever Code

### `{file}:{line}`
```python
{the clever code}
```
**What it does:** {explanation}
**Why clever is bad here:** {reason}
**Clearer version:**
```python
{clearer code}
```

## Summary

| Category | Count | Accidental |
|----------|-------|------------|
| Cognitive hotspots | {N} | {N} |
| Mixed concerns | {N} | {N} |
| Deep nesting | {N} | {N} |
| Clever code | {N} | {N} |

## Questions for Craft Pass

- {specific questions about potential deletions/simplifications}
```

---

## Pass 4: Craft

```
{PREAMBLE with pass_name="craft"}

PREVIOUS: Read all previous passes first.

QUESTION: What would antirez delete or simplify?

You are the final judge. Armed with full context from previous passes,
find what doesn't earn its existence.

> "The best code is no code at all." — antirez

TASKS:

1. DELETION CANDIDATES
   - Dead code (0 callers)
   - Commented-out code
   - Vestigial features (TODO/DEPRECATED)
   - "Just in case" code that's never triggered

2. UNEARNED ABSTRACTION
   - Interface with 1 implementation
   - Generic used for 1 type
   - Factory that just returns `Thing()`
   - Base class with 1 subclass

3. UNNECESSARY INDIRECTION
   - Wrapper that just calls wrapped
   - Delegation chain: A→B→C→D for simple operation
   - "Service" that's a function pretending to be a class

4. PROSE CHECK
   - Could a stranger read this in 2 minutes?
   - Are names self-documenting?
   - Do comments explain WHY, not WHAT?

EARNED ABSTRACTION (NOT FINDINGS):

- 3+ implementations = earned interface
- Generic that documents type relationships = earned
- Layer that isolates genuine complexity = earned
- Indirection that reveals intent = earned

FINDINGS FORMAT:

```markdown
# Craft Pass: {target}

## Deletion Candidates

### 1. {what} @ {file}:{line}
**Type:** dead code / commented / vestigial / just-in-case
**Evidence:**
```bash
# Search for callers
{grep command and result showing 0 callers}
```
**Lines to delete:** {N}
**Risk:** None / Low / Check with owner

### 2. ...

## Unearned Abstraction

### 1. `{AbstractThing}` @ {file}:{line}
**Type:** interface / generic / factory / base class
**Implementations:** {N} (need 3+ to be earned)

```python
{the abstraction}
```

**Concrete replacement:**
```python
{what it should be instead}
```

**Savings:** {lines removed} lines, {complexity removed} indirection

## Unnecessary Indirection

### 1. {A} → {B} → {C} for {operation}
**The chain:**
```python
# A calls B
{code}

# B calls C
{code}

# C does the work
{code}
```

**Direct version:**
```python
# A does the work directly
{code}
```

**Why this is better:** {explanation}

## Prose Failures

### `{function_name}` @ {file}:{line}
**Time to read:** {>2 minutes}
**Problem:** {what's unclear}
**Fix:** {rename / add why-comment / restructure}

## Summary

| Category | Items | Lines Recoverable |
|----------|-------|-------------------|
| Deletion candidates | {N} | {N} |
| Unearned abstraction | {N} | {N} |
| Unnecessary indirection | {N} | {N} |
| Prose failures | {N} | - |

## Priority Ranking

1. **P0 (do now):** {list with file:line}
2. **P1 (do soon):** {list with file:line}
3. **P2 (consider):** {list with file:line}
```
