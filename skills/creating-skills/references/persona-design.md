# Orthogonal Persona Design

For parallel skills, personas must have distinct territories to avoid overlap and surface diverse insights.

## Why Orthogonality Matters

Overlapping personas:
- Same issue flagged 4 times
- No new perspectives surfaced
- Wasted parallel capacity

Orthogonal personas:
- Each surfaces unique insights
- No redundant findings
- Full coverage of problem space

---

## The One-Question Rule

Each persona answers exactly ONE question:

| Persona | Question |
|---------|----------|
| Devil's Advocate | "What's WRONG?" |
| Gap Finder | "What's MISSING?" |
| Simplicity Reviewer | "Is this GOOD?" |
| Security Auditor | "What's EXPLOITABLE?" |

**Not questions like:**
- "What do you think?" (too vague)
- "Review this" (no focus)
- "Find issues" (overlaps with others)

---

## Territory Boundaries

Each persona owns specific issue types:

| Persona | Territory | NOT Territory |
|---------|-----------|---------------|
| Devil's Advocate | Bugs, contradictions, logic errors | Style, missing features |
| Gap Finder | Omissions, edge cases, missing validation | Existing bugs, style |
| Simplicity Reviewer | Over-engineering, unnecessary complexity | Correctness, security |
| Security Auditor | Vulnerabilities, auth issues, injection | Style, complexity |

---

## "NOT Your Territory" Sections

Every persona prompt MUST include explicit exclusions:

```markdown
## Your Question
"What's WRONG with this code?"

## Your Territory
- Logic errors
- Contradictions between code and comments
- Race conditions
- Incorrect assumptions

## NOT Your Territory (Do NOT flag these)
- Missing features (Gap Finder handles this)
- Style/formatting issues (Simplicity Reviewer handles this)
- Security vulnerabilities (Security Auditor handles this)
- Performance issues (not in scope for this skill)
```

---

## Common Persona Sets

### For Code Review (5 personas)

| Persona | Question | Territory |
|---------|----------|-----------|
| Devil's Advocate | "What's WRONG?" | Bugs, logic errors |
| Gap Finder | "What's MISSING?" | Edge cases, validation |
| antirez Reviewer | "Is this GOOD?" | Complexity, elegance |
| Security Auditor | "What's EXPLOITABLE?" | Vulnerabilities |
| Doc Verifier | "Is this REAL?" | Hallucinated APIs, wrong imports |

### For Research (3 personas)

| Persona | Question | Territory |
|---------|----------|-----------|
| Explorer A | "What does Source Type A say?" | Official docs, specs |
| Explorer B | "What does Source Type B say?" | Real-world usage, examples |
| Explorer C | "What does Source Type C say?" | Edge cases, gotchas |

### For Critique (3 personas)

| Persona | Question | Territory |
|---------|----------|-----------|
| Skeptic | "What WILL fail?" | Concrete failure modes |
| Gap Finder | "What's MISSING?" | Omissions, assumptions |
| Simplifier | "What's UNNECESSARY?" | Over-engineering |

---

## Designing New Personas

### Step 1: List All Issue Types

What kinds of issues could exist?
- Bugs, logic errors
- Missing validation
- Security holes
- Over-complexity
- Documentation gaps
- Performance issues
- etc.

### Step 2: Group into Orthogonal Categories

| Category | Issue Types |
|----------|-------------|
| Correctness | Bugs, logic errors, race conditions |
| Completeness | Missing validation, edge cases, gaps |
| Quality | Complexity, style, maintainability |
| Security | Auth, injection, data exposure |

### Step 3: Assign One Persona Per Category

| Persona | Category | Question |
|---------|----------|----------|
| Correctness Checker | Correctness | "What's broken?" |
| Completeness Checker | Completeness | "What's missing?" |
| Quality Checker | Quality | "What's over-engineered?" |
| Security Checker | Security | "What's exploitable?" |

### Step 4: Write Territory Boundaries

For each persona, explicitly list:
1. What's IN territory
2. What's NOT in territory (cite which persona handles it)

---

## Hard Output Limits

Force prioritization by limiting output:

```markdown
## Output Limits (CRITICAL)

Report AT MOST:
- **1 Blocker** - The ONE issue that blocks shipping tonight
- **3 Polish** - Important but shippable
- **3 Skipped** - Considered but not worth flagging

**If you find 10 issues, CHOOSE THE WORST ONE.**

Zero blockers is valid - means this persona found nothing blocking.
```

### Why Limits Matter

Without limits:
- Personas report everything
- 5 personas × 10 issues = 50 findings
- No prioritization, can't act

With limits:
- 5 personas × 1 blocker = 5 max blockers
- Forced prioritization
- Actionable output

---

## Conditional Personas

Some personas only apply in certain contexts:

```markdown
## Conditional Personas

### Security Auditor
**Include when:**
- User input handling
- Auth/authz changes
- External API integration
- Code with "api", "auth", "user", "token" in path

**Skip when:**
- Internal refactoring
- Test changes
- Dashboard/admin tools
```

---

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Vague questions ("review this") | One specific question per persona |
| Overlapping territory | Explicit "NOT Your Territory" sections |
| No output limits | Hard caps: 1 blocker, 3 polish, 3 skipped |
| All personas always run | Conditional inclusion based on context |
| Same persona different name | Ensure genuinely orthogonal perspectives |
