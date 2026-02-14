# Skill Critique Framework

Evaluate skill quality before Final Gate. Find weaknesses, not praise.

---

## The Critique

Apply after drafting `<role>`, `<purpose>`, `<workflow>`, `<rules>`. Fix all critical issues before proceeding.

### Pass 1: Role Quality

| Check | Failure |
|-------|---------|
| WHO is 2-4 word noun phrase? | "Systematic analyzer who reviews code" → "Code auditor" |
| WHO is concrete enough to hire? | "Helper" fails. "Security auditor" passes. |
| ATTITUDE states consequence? | "Start fast" fails. "Slow starts lose context." passes. |
| ATTITUDE ≤10 words? | Trim or split. |

### Pass 2: Purpose Punch

| Check | Failure |
|-------|---------|
| Starts with "Your job is"? | "This skill helps..." → rewrite |
| Core job clear in first 10 words? | If not, front-load the verb |
| Consequence clause present? | Why does this matter? What fails without it? |
| Would a random dev understand? | Jargon without context fails |

### Pass 3: Workflow Completeness

| Check | Failure |
|-------|---------|
| Fresh Claude can execute step 1 without questions? | Missing: what file? what scope? what format? |
| Each step has clear output? | "Analyze the code" → what artifact? |
| Steps are sequential (order matters)? | If not, why numbered? |
| No implicit knowledge assumed? | "Check the usual places" fails |

### Pass 4: Rules Power

| Check | Failure |
|-------|---------|
| Each rule prevents a specific failure mode? | "Be thorough" prevents nothing |
| Rules state consequences, not process? | "Always verify" → "Unverified claims ship bugs." |
| Could you test rule compliance? | Vague rules can't be checked |
| Any rules that are just workflow restatements? | Delete duplicates |

### Pass 5: Anti-Pattern Scan

| Pattern | Fix |
|---------|-----|
| Hedge words (might, could, perhaps, consider) | Delete or commit |
| Passive voice (should be used, can be done) | Rewrite active |
| Third person (This skill, It will, The user) | Second person |
| Filler words (basically, essentially, in order to) | Delete |
| Process over consequence ("Always do X" vs "X prevents Y") | State why |

---

## Output Format

```
SKILL CRITIQUE (internal):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Critical Issues (must fix):
1. [Section]: [Issue] → [Fix]

Weak Points (should fix):
1. [Section]: [Issue] → [Improvement]

Verdict: [READY | NEEDS WORK]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Example Critique

**Skill being critiqued:**
```xml
<role>
WHO: Code reviewer
ATTITUDE: Find all the issues
</role>

<purpose>
This skill helps review code for problems and suggests improvements.
</purpose>

<workflow>
1. Look at the code
2. Find issues
3. Report findings
</workflow>

<rules>
- Be thorough
- Check everything
</rules>
```

**Critique:**
```
SKILL CRITIQUE (internal):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Critical Issues (must fix):
1. PURPOSE: "This skill helps" is third person → "Your job is to hunt bugs before they ship."
2. WORKFLOW: "Look at the code" is vague → "Read target file, note line numbers of concerns"
3. WORKFLOW: No output artifact specified → Add "Write findings to {outputs}/review.md"
4. RULES: "Be thorough" prevents nothing → "Skipped lines hide bugs."

Weak Points (should fix):
1. ROLE: "Code reviewer" too generic → "Bug hunter" or "Security auditor"
2. ATTITUDE: "Find all the issues" is goal not consequence → "Missed bugs ship to prod."
3. WORKFLOW: Step 2 "Find issues" duplicates purpose → Delete or specify technique

Verdict: NEEDS WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Integration

1. **Run after drafting** — before showing skill to user
2. **Fix critical issues** — no exceptions
3. **Re-critique if major changes** — max 2 iterations
4. **Only proceed to Final Gate when READY**
