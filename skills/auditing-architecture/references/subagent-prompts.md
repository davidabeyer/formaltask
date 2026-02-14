# Subagent Prompts

Exact prompts for each phase's subagent. Copy-paste ready.

---

## Phase 1: Architecture Mapping

```
PHASE 1: ARCHITECTURE MAPPING for Deep Code Audit

TARGET: {target_path}
WORKING DIR: {working_dir}

Your job: Build complete mental model before any criticism.
This handoff must be SELF-CONTAINED. No references to prior context.

RESEARCH TASKS:

1. MODULE DISCOVERY
   - Use Glob to find all code directories
   - Read __init__.py / index files for module purposes
   - Map the module hierarchy

2. DATA FLOW
   - Where does data enter the system?
   - How is it transformed?
   - Where does it exit?

3. KEY ABSTRACTIONS
   - Find base classes, protocols, interfaces
   - Count implementations of each
   - Note which are justified (2+ implementations)

4. TRACED PATHS
   - Pick 3-5 representative operations
   - Trace from entry to completion
   - Document the journey with file:line references

5. DESIGN PHILOSOPHY
   - What patterns recur?
   - What conventions exist?
   - What seems intentional vs accidental?

TOOLS TO USE:
- mcp__auggie-mcp__codebase-retrieval for semantic search
- mcp__morph-mcp__warpgrep_codebase_search for pattern finding
- Glob for file discovery
- Read for full file examination

OUTPUT: Write to {working_dir}/01-architecture-mapping.md

FORMAT:
```markdown
# Architecture Mapping: {project_name}

## Purpose
{2-3 sentences on what this codebase does}

## Module Map
| Module | Path | Responsibility | Key Files |
|--------|------|----------------|-----------|
| {name} | {path} | {purpose} | {files with line counts} |

## Data Flow
```
Input: {sources}
   ↓
{step 1}
   ↓
{step 2}
   ↓
Output: {destinations}
```

## Key Abstractions
| Abstraction | Purpose | Implementations | Justified? |
|-------------|---------|-----------------|------------|
| {name} | {why it exists} | {count} | {yes/no + reason} |

## Traced Paths

### Path 1: {operation name}
`{entry}` → `{step1}` → `{step2}` → `{result}`

**Files involved:**
- {file1}:{lines} - {role in this path}
- {file2}:{lines} - {role in this path}

**Insight:** {what this reveals about design}

### Path 2: {operation name}
...

## Design Philosophy
{Inferred from patterns}
- {principle 1}: {evidence}
- {principle 2}: {evidence}

## Open Questions
{Things still unclear - investigate during module analysis}
```

Be thorough. Fresh context will continue from this handoff.
```

---

## Phase 3: Deep Module Analysis

```
PHASE 3: DEEP MODULE ANALYSIS

MODULE: {module_name}
PATH: {module_path}
PURPOSE: {module_purpose}
WORKING DIR: {working_dir}

CONTEXT (from architecture mapping):
{architecture_summary - paste relevant section}

Your job: Find actual problems in this module through deep comprehension.

ANALYSIS PROTOCOL:

STEP 1: COMPLETE COMPREHENSION (before any criticism)
- Read EVERY file in {module_path}
- List all public functions/classes
- Understand what each does
- Trace 3-5 execution paths through this module

STEP 2: SUMMARIZE UNDERSTANDING
Before any findings, write:
"This module exists to {purpose}. It works by {mechanism}.
The author structured it this way because {inferred reasoning}."

STEP 3: APPLY QUALITY CRITERIA

### Criterion 1: SIMPLICITY
- Does each function do one thing?
- Are responsibilities clearly separated?
- Red flag: function with 5+ distinct operations

### Criterion 2: CLARITY
- Can I understand each function in 2 minutes?
- Is control flow obvious?
- Red flag: need to trace 10 files to understand

### Criterion 3: DATA VISIBILITY
- Can I see what data exists and its state?
- Is state concentrated or scattered?
- Red flag: data hidden behind layers of getters

### Criterion 4: NECESSITY
- Does each abstraction earn its existence?
- Are there ABCs with only 1 implementation?
- Red flag: 5-layer indirection for simple operation

### Criterion 5: TEST HONESTY
- Do tests actually test what they claim?
- Do assertions match test names?
- Red flag: `test_validates_X` with no validation assertion

### Criterion 6: LIVENESS
- Is all code reachable?
- Are there functions with 0 callers?
- Red flag: commented-out code, dead branches

STEP 4: DOCUMENT FINDINGS
For each genuine issue:
- Location (file:line)
- Current code (quoted, 5+ lines context)
- The problem (specific, in this context)
- The impact (concrete, not theoretical)
- Proposed fix (before/after code)

OUTPUT: Write to {working_dir}/03-module-{module_name}-analysis.md

FORMAT:
```markdown
# Deep Analysis: {module_name}

## Module Understanding

**Purpose:** {what this module does}
**Mechanism:** {how it works}
**Design Intent:** {why it's structured this way}

## Public Interface

### Functions
| Function | Purpose | Signature |
|----------|---------|-----------|
| {name} | {what} | {params → return} |

### Classes
| Class | Purpose | Key Methods |
|-------|---------|-------------|
| {name} | {what} | {methods} |

## Evaluation by Criterion

### Simplicity
**Assessment:** {pass | findings}
{details}

### Clarity
**Assessment:** {pass | findings}
{details}

### Data Visibility
**Assessment:** {pass | findings}
{details}

### Necessity
**Assessment:** {pass | findings}
{details}

### Test Honesty
**Assessment:** {pass | findings}
{details}

### Liveness
**Assessment:** {pass | findings}
{details}

## Findings

### Finding 1: {title}
**Location:** `{file}:{lines}`
**Criterion:** {which quality criterion}
**Severity:** {critical|significant|minor}

**Current code:**
```python
{actual code with 5+ lines context}
```

**The problem:**
{Specific explanation - why this is wrong IN THIS CONTEXT}

**The impact:**
{Concrete impact - bugs, confusion, maintenance burden}

**Proposed fix:**
```python
{improved code}
```

**Verification notes:**
{What to check in Phase 4}

---

### Finding 2: {title}
...

## Summary

| Criterion | Status | Findings |
|-----------|--------|----------|
| Simplicity | {pass/findings} | {count} |
| Clarity | {pass/findings} | {count} |
| Data Visibility | {pass/findings} | {count} |
| Necessity | {pass/findings} | {count} |
| Test Honesty | {pass/findings} | {count} |
| Liveness | {pass/findings} | {count} |

## Notes for Verification Phase
{Findings that need extra scrutiny}
{Patterns to check consistency of}
```

CRITICAL RULES:
- Include actual code, not descriptions
- File:line for every reference
- Understand BEFORE criticizing
- "Could be better" is not a finding
```

---

## Phase 4: Adversarial Verification

```
PHASE 4: ADVERSARIAL VERIFICATION

WORKING DIR: {working_dir}

Read all module analyses: {working_dir}/03-module-*.md

Your job: Attempt to DISPROVE every finding. Only confirmed findings survive.

VERIFICATION PROTOCOL:

For EACH finding in the analyses:

### Step 1: Search for Explanation
- Read comments around the flagged code
- Check git blame: `git blame -L {start},{end} {file}`
- Read the commit message: `git log -1 --format='%B' {commit}`
- Search for design docs mentioning this pattern

### Step 2: Check Consistency
- Is this pattern used elsewhere in the codebase?
- If consistent, might be intentional convention
- Search: `Grep(pattern="{pattern}")`

### Step 3: Trace All Callers
- Find every call site: `Grep(pattern="{function_name}\\(")`
- For each caller, understand the context
- Does the "problem" actually cause issues in practice?

### Step 4: Evaluate the Fix
- Write out the proposed fix completely
- Does it compile/parse?
- Does it maintain all existing behavior?
- Does it introduce new problems?
- Is it actually simpler, or just different?

### Step 5: Impact Assessment
| Level | Criteria |
|-------|----------|
| Critical | Causes bugs, security issues, data loss |
| Significant | Slows development, causes confusion |
| Minor | Aesthetic, slight improvement |
| Negligible | Personal preference → REJECT |

VERDICTS:

**CONFIRMED** - Finding survives verification
- No good explanation found
- Fix is sound
- Impact justifies change

**REJECTED** - Finding fails verification
- Intentional design (explain why)
- Consistent pattern (codebase convention)
- Fix would break callers
- Impact negligible (preference only)

**MODIFIED** - Finding partially correct
- Core issue valid
- Scope or approach needs adjustment
- Provide revised finding

OUTPUT: Write to {working_dir}/04-verified-findings.md

FORMAT:
```markdown
# Verification Results

## Summary
- Findings reviewed: {N}
- Confirmed: {N}
- Rejected: {N}
- Modified: {N}

## Confirmed Findings

### 1. {title}
**Module:** {name}
**Original location:** `{file}:{lines}`
**Severity:** {critical|significant|minor}

**Original finding:**
{quote from module analysis}

**Verification:**
- Explanation search: {found/none}
- Consistency check: {consistent/inconsistent}
- Caller analysis: {N callers, impact assessment}
- Fix evaluation: {sound/problematic}

**Verdict: CONFIRMED**
**Evidence:** {why this is a real issue}

---

### 2. {title}
...

## Rejected Findings

### {title}
**Module:** {name}
**Original finding:** {summary}

**Verdict: REJECTED**
**Reason:** {specific reason}
**Evidence:** {what was found}

---

## Modified Findings

### {title}
**Module:** {name}
**Original finding:** {what was claimed}
**Issue:** {what was wrong with original}

**Revised finding:**
{better framed issue with evidence}

**Verdict: MODIFIED**
```
```

---

## Phase 5: Synthesis

```
PHASE 5: SYNTHESIS

WORKING DIR: {working_dir}

Read:
- Architecture mapping: {working_dir}/01-architecture-mapping.md
- Verified findings: {working_dir}/04-verified-findings.md

Your job: Create final audit report with prioritized recommendations.

SYNTHESIS TASKS:

1. EXECUTIVE SUMMARY
   - Overall code health
   - Key findings (critical first)
   - Recommended priority

2. UNDERSTANDING SUMMARY
   - What the code does (from architecture)
   - How it's structured
   - Design philosophy identified

3. VERIFIED FINDINGS
   - Grouped by severity
   - Each with full evidence and fix
   - Prioritized recommendations

4. REJECTED FINDINGS
   - For transparency
   - Shows verification was thorough

5. RECOMMENDATIONS
   - Priority order with rationale
   - Quick wins vs larger efforts
   - Dependencies between fixes

OUTPUT: Write to {working_dir}/05-final-report.md

Also save via:
```python
from formaltask.utils.skill_output import write_skill_report
write_skill_report(
    skill="auditing-code-deeply",
    title=f"Deep Audit: {target_name}",
    content=report
)
```

FORMAT: See output-template.md
```
