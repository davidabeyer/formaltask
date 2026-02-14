# Comprehension Phase Protocol

Before writing any documentation, build genuine understanding of the code.

## Why This Matters

Surface-level reading produces incorrect documentation:
- A function's name might not reflect its actual behavior
- Edge cases are invisible without tracing execution
- Design rationale lives in git history and comments
- "Simple" code often has subtle important behaviors

**Understanding first prevents embarrassing incorrect docs.**

---

## Comprehension Steps

### Step 1: Read ALL Files

Don't skim. Don't grep for keywords. Read every file in the target area.

```python
# Get all files
files = Glob(f"{target_area}/**/*.py")  # Adjust for language

# Read each one completely
for file in files:
    Read(file)  # Full file, not grep matches
```

**Note as you read:**
- Purpose of each file (from docstring, comments, behavior)
- Key functions/classes and what they do
- Connections to other files
- Anything surprising or non-obvious

### Step 2: Trace Execution Paths

Select 3-5 representative paths through the code.

**Path selection criteria:**
1. Happy path (normal usage)
2. Error path (what happens on failure)
3. Edge case (unusual but valid input)
4. Integration path (how it connects to other modules)

**For each path:**
```python
# Start at entry point
Read("target/main.py")  # Find where execution starts

# Follow each call
Read("target/handler.py")  # What does the entry point call?
Read("target/processor.py")  # What does the handler call?
Read("target/output.py")  # Where does data end up?

# Document the chain with actual code
"""
Entry: main.py:45 run_command()
  → handler.py:23 process_input()
  → processor.py:78 transform()
  → output.py:12 write_result()
"""
```

### Step 3: Find Design Rationale

Code tells you WHAT. Git and comments tell you WHY.

```bash
# Check git history for design decisions
git log --oneline -20 -- {target_area}

# Check for explanatory commit messages
git log --format="%s%n%b" -5 -- {file}

# Check blame for specific lines
git blame -L 45,60 {file}
```

**Look for:**
- Commit messages explaining "why" not just "what"
- Comments that explain non-obvious decisions
- TODO/FIXME/HACK comments (document known issues)
- Design docs if they exist

### Step 4: Identify Edge Cases

What happens when things go wrong or inputs are unusual?

```python
# Look for exception handling
Grep(pattern="except|raise|try:", path=target_area)

# Look for validation
Grep(pattern="if.*not|if.*None|assert", path=target_area)

# Look for defaults and fallbacks
Grep(pattern="or |default|fallback", path=target_area)
```

**Document each edge case:**
- What triggers it?
- What happens?
- Is this behavior intentional?

---

## Comprehension Checkpoint

Before proceeding to documentation, answer these questions:

### 1. Purpose
> What problem does this code solve?

Not "what does it do" but "why does it exist?"

### 2. Mechanism
> How does it solve the problem?

High-level flow, not line-by-line.

### 3. Key Abstractions
> What are the core concepts?

Classes, functions, data structures that matter.

### 4. Edge Cases
> What are the boundary conditions?

Errors, empty inputs, concurrent access, etc.

### 5. Surprises
> What would surprise a reader?

Non-obvious behavior, historical baggage, known issues.

**If you cannot answer all five, continue reading. Do not document.**

---

## Working File Format

Write comprehension to: `{working_dir}/03-comprehension.md`

```markdown
# Comprehension: {target}

## Purpose
{What problem this code solves - 2-3 sentences}

## Mechanism
{How it works at a high level}

```
Input: {what comes in}
   ↓
{transformation steps}
   ↓
Output: {what comes out}
```

## Key Abstractions

| Abstraction | Purpose | Key Methods |
|-------------|---------|-------------|
| {class/function} | {why it exists} | {important methods} |

## Traced Paths

### Path 1: {name} (Happy Path)
`{entry}` → `{step1}` → `{step2}` → `{output}`

**What happens:** {description}

### Path 2: {name} (Error Path)
`{entry}` → `{step1}` → `{error}` → `{handling}`

**What happens:** {description}

## Edge Cases

| Condition | Behavior | Intentional? |
|-----------|----------|--------------|
| {trigger} | {what happens} | {yes/no/unclear} |

## Design Rationale
{Why the code is structured this way - from git, comments, inference}

## Surprises
{Non-obvious behaviors that documentation should highlight}

## Open Questions
{Things unclear - may need to investigate or document as "unknown"}
```

---

## Common Comprehension Failures

| Failure | Consequence | Prevention |
|---------|-------------|------------|
| Skimmed instead of read | Missed key behavior | Read every file completely |
| Only read entry points | Missed internal logic | Trace full execution paths |
| Ignored error handling | Documented only happy path | Explicitly trace error paths |
| Assumed from names | Documented wrong behavior | Verify behavior in code |
| Skipped git history | Missed design rationale | Check blame and log |
