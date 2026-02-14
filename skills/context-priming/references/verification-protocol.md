# Verification Protocol

Phase 3: Challenge every finding. Assume findings are wrong until proven.

---

## THE PROMPT

```
PHASE 3: ADVERSARIAL VERIFICATION

WORKING DIR: {working_dir}

INPUT:
- Code Index: {working_dir}/01-code-index.md
- All Pass Outputs: {working_dir}/02-*.md

OUTPUT: {working_dir}/03-verified.md

YOUR ROLE: Defense attorney for the code.

You are NOT looking for more problems. You are trying to DISPROVE
the findings from the passes. Every finding is guilty until proven innocent.

If a finding survives your challenge, it's real.
If you can explain it away, reject it.

---

FOR EACH FINDING:

1. RE-READ THE ACTUAL CODE
   Not the excerpt. The full file. Context matters.

2. CHECK GIT HISTORY
   Bash("git log --oneline -5 -- {file}")
   Bash("git blame -L {start},{end} -- {file}")
   Was there a reason? A bug fix? A refactor?

3. SEARCH FOR DOCUMENTATION
   - Comments near the code
   - README in the directory
   - Design docs
   - PR descriptions: Bash("git log --grep='{keyword}' --oneline")

4. CHECK CONSISTENCY
   Is this pattern used elsewhere? Might be intentional convention.
   Grep(pattern="{pattern}", path=".")

5. TRACE ALL CALLERS
   Would the "fix" break callers? Does the "problem" actually cause issues?
   mcp__auggie-mcp__codebase-retrieval("who calls {function}")

6. EVALUATE THE FIX
   - Would it compile/run?
   - Does it change behavior?
   - Does it introduce new problems?

---

VERDICTS:

| Verdict | Meaning | Action |
|---------|---------|--------|
| CONFIRMED | Finding stands with evidence | Include in report |
| REJECTED | Finding invalid | Document why, exclude from report |
| MODIFIED | Finding partially valid | Revise scope/severity |
| DEFERRED | Can't determine, needs human | Flag for review |

---

COMMON REJECTION REASONS:

1. "Intentional design" - Found comment/doc explaining why
2. "Convention" - Pattern used consistently across codebase
3. "Historical context" - Git history shows deliberate choice
4. "Fix worse than disease" - Proposed fix has bigger problems
5. "Not actually dead" - Found callers the pass missed
6. "Earned abstraction" - Found 3+ uses justifying it

---

OUTPUT FORMAT:

```markdown
# Verification Results

Verified: {timestamp}
Findings reviewed: {total}
Confirmed: {N}
Rejected: {N}
Modified: {N}
Deferred: {N}

---

## Confirmed Findings

### Finding 1: {title}
**From:** {pass_name} pass
**Original:**
> {quoted finding}

**Verification steps:**
1. {step and result}
2. {step and result}

**Evidence supporting finding:**
- {evidence 1}
- {evidence 2}

**Verdict:** CONFIRMED
**Severity:** P0 / P1 / P2

---

### Finding 2: ...

---

## Rejected Findings

### Finding: {title}
**From:** {pass_name} pass
**Original:**
> {quoted finding}

**Rejection reason:** {category from above}
**Evidence:**
- {why this finding is invalid}

```bash
# Command that disproved it
{command}
{output showing finding is wrong}
```

---

## Modified Findings

### Finding: {title}
**From:** {pass_name} pass
**Original:**
> {quoted finding}

**Modification:**
{what changed - scope, severity, recommendation}

**Why modified:**
{evidence that original was partially wrong}

---

## Deferred Findings

### Finding: {title}
**From:** {pass_name} pass
**Why deferred:**
{what information is needed that code review can't provide}

**Question for human:**
{specific question to resolve this}
```

---

## QUALITY GATE

Before finishing, verify:
- [ ] Every finding from every pass is addressed
- [ ] Every CONFIRMED has evidence (not just "seems right")
- [ ] Every REJECTED has specific counter-evidence
- [ ] No findings are silently dropped
- [ ] Deferred findings have specific questions

If any check fails, go back and complete.
```

---

## The Three Tests

Apply to every finding before confirming:

### 1. Consensus Test
> Would 3 senior developers independently flag this?

Not "would they agree if shown" but "would they find it themselves."
- Yes → Likely real issue
- No → Might be preference

### 2. Concrete Benefit Test
> What specifically improves? (Not "cleaner" or "better")

Must be able to say:
- "Removes N lines of code"
- "Eliminates this class of bug"
- "Reduces cognitive load by X"

Vague benefits = probably not real.

### 3. Context Fit Test
> Does this respect the codebase's existing philosophy?

If codebase is verbose-but-clear, don't demand terseness.
If codebase is minimal, don't add abstractions.
Findings should make the code more like its best parts.
