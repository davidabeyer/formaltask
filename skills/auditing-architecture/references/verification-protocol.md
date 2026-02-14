# Adversarial Verification Protocol

Every finding must survive active attempts to disprove it.

## Why Verification Matters

Unverified findings often turn out to be:
- **Preferences disguised as problems** - "I would write it differently"
- **Context-blind complaints** - Ignoring why the code exists
- **False positives** - Pattern matched but not actually wrong
- **Harmful suggestions** - Fix would break something

**Goal:** Only report findings that are genuinely actionable improvements.

---

## The Verification Mindset

Adopt the perspective of:
1. **The original author** - Why might they have written it this way?
2. **A skeptical reviewer** - Is this criticism valid or nitpicking?
3. **The person who has to fix it** - Will this fix actually improve things?

---

## Verification Steps

For EACH finding, execute ALL steps.

### Step 1: Search for Explanation

Check if the code is intentional:

```python
# Check for comments explaining the decision
Read(file_path)  # Look above the flagged code

# Check git blame for context
Bash(f"git blame -L {start_line},{end_line} {file_path}")

# Read the commit message
Bash(f"git log -1 --format='%B' {commit_hash}")

# Check for related design docs
Grep(pattern=f"{function_name}|{class_name}", path="docs/")
```

**Outcome:**
- Found explanation → Re-evaluate finding in light of context
- No explanation → Continue verification

### Step 2: Check Consistency

Is this pattern used elsewhere?

```python
# Search for similar patterns
Grep(pattern="{pattern_from_finding}")

# Check if it's a codebase convention
mcp__auggie-mcp__codebase-retrieval(
    "Find similar patterns to {description}"
)
```

**Outcome:**
- Consistent pattern → Might be intentional design decision
- Inconsistent → More likely an issue worth fixing

### Step 3: Trace All Callers

Understand actual usage:

```python
# Find all call sites
Grep(pattern=f"{function_name}\\(")

# For each caller, understand the context
for caller in callers:
    Read(caller_file)
    # How is this function actually used?
    # Does the "problem" manifest in practice?
```

**Questions:**
- Does the code work correctly for all actual use cases?
- Would the suggested fix break any callers?
- Is the "issue" theoretical or practical?

### Step 4: Evaluate the Fix

Before confirming, verify the fix is sound:

```python
# Write out the proposed fix (mentally or on paper)
# Ask:
# 1. Does this compile/parse?
# 2. Does this maintain all existing behavior?
# 3. Does this introduce new problems?
# 4. Is this actually simpler or just different?
```

**Red flags in proposed fixes:**
- Changes behavior (bug risk)
- Adds complexity elsewhere
- Requires touching many files
- Based on assumptions about future needs

### Step 5: Impact Assessment

Quantify the value:

| Impact Level | Description | Action |
|--------------|-------------|--------|
| **Critical** | Causes bugs, security issues, data loss | Must fix |
| **Significant** | Slows development, causes confusion | Should fix |
| **Minor** | Aesthetic, slight improvement | Consider fixing |
| **Negligible** | Personal preference | Do not report |

---

## Verification Verdicts

After all steps, assign one verdict:

### CONFIRMED

The finding survives all verification:
- No good explanation for current code
- Fix is sound and improves things
- Impact justifies the change

```markdown
**Verdict: CONFIRMED**
**Evidence:**
- No explanation in comments/commits
- Pattern is inconsistent with rest of codebase
- Fix verified to maintain behavior
- Impact: {critical|significant|minor}
```

### REJECTED

The finding fails verification:

```markdown
**Verdict: REJECTED**
**Reason:** {specific reason}
**Evidence:** {what you found}
```

Common rejection reasons:
- "Intentional design - commit message explains {reason}"
- "Consistent pattern throughout codebase"
- "Fix would break {specific caller}"
- "Impact negligible - aesthetic preference only"

### MODIFIED

Original finding was partially correct:

```markdown
**Verdict: MODIFIED**
**Original Finding:** {what you initially thought}
**Revised Finding:** {what's actually the issue}
**Change Reason:** {what you learned during verification}
```

---

## Verification Working File

Write verification results to: `{working_dir}/verified-findings.md`

```markdown
# Verification Results

## Finding 1: {title}

### Original Assessment
{From Phase C}

### Verification Checks

**Explanation Search:**
- Comments: {found/none}
- Git blame: {commit msg}
- Docs: {found/none}
- Conclusion: {explained/unexplained}

**Consistency Check:**
- Similar patterns: {count}
- Codebase convention: {yes/no}
- Conclusion: {consistent/inconsistent}

**Caller Analysis:**
- Call sites: {count}
- Usage contexts: {summary}
- Fix impact: {none/low/high}

**Fix Evaluation:**
- Compiles: {yes/no}
- Behavior preserved: {yes/no}
- New problems: {none/list}
- Actually simpler: {yes/no/different}

**Impact Assessment:** {critical/significant/minor/negligible}

### Verdict: {CONFIRMED|REJECTED|MODIFIED}
{Evidence summary}

---

## Finding 2: {title}
{repeat structure}
```

---

## Common Verification Failures

| Failure | Example | Prevention |
|---------|---------|------------|
| Skipped git blame | Missed "WORKAROUND: bug in library X" | Always check history |
| Ignored callers | Fix broke 3 call sites | Trace all usages |
| Assumed fix works | Proposed code doesn't compile | Actually write the fix |
| Reported preference | "I'd use dict comprehension" | Check if actually better |
| Counted all findings | 10 findings, 2 significant | Only report verified |
