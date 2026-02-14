# Mode System Design

Modal skills adapt to task complexity. This reference covers patterns for designing effective tier systems.

## Why Modes Matter

Without modes, skills either:
- **Over-deliver** - Deep analysis for trivial tasks (wasted time)
- **Under-deliver** - Surface checks for critical tasks (missed issues)

Modes let Claude match effort to stakes.

---

## Mode Design Principles

### 1. Observable Selection Criteria

**Bad criteria (vague):**
```markdown
| Mode | When |
|------|------|
| Quick | Simple tasks |
| Deep | Complex tasks |
```

**Good criteria (observable):**
```markdown
| Mode | When |
|------|------|
| Quick | Single file, known format, user says "quick" |
| Deep | User says "thorough", production deploy, security-relevant |
```

Claude can evaluate "user says X" or "file count". Claude cannot evaluate "complex."

### 2. Distinct Workflows (Not Just Depth)

**Bad modes (just more steps):**
```markdown
Quick: Steps 1-2
Standard: Steps 1-4
Deep: Steps 1-6
```

**Good modes (different approaches):**
```markdown
Quick: Direct response, no verification
Standard: Structured report with severity levels
Deep: Parallel subagents + adversarial review + synthesis
```

### 3. Explicit Default

Always state the default:

```markdown
Default to **Standard**. Use Quick for {condition}. Use Deep when {condition}.
```

Never make Claude guess.

---

## Common Mode Patterns

### Pattern A: Depth Scaling

| Mode | Subagents | Output |
|------|-----------|--------|
| Quick | 0 | Direct response |
| Standard | 3 | Structured report |
| Deep | 5+ | Full audit |

**Use when:** Analysis quality scales with parallel exploration.

### Pattern B: Verification Scaling

| Mode | Verification | Output |
|------|--------------|--------|
| Quick | None | Fast result |
| Standard | Single-pass | Confidence level |
| Deep | Multi-pass + adversarial | Verified result |

**Use when:** Confidence matters more than breadth.

### Pattern C: Scope Scaling

| Mode | Scope | Output |
|------|-------|--------|
| Quick | Single item | Item analysis |
| Standard | Related items | Cross-reference analysis |
| Deep | Full system | Dependency + impact analysis |

**Use when:** Blast radius matters.

---

## Mode Selection Signals

### Quick Mode Signals

- User says: "quick", "fast", "just check"
- Single file/item
- Known format/pattern
- Low stakes (personal config, draft code)
- Time pressure explicit

### Standard Mode Signals

- Default (no signals either way)
- Multiple files/items
- Unknown format/pattern
- Moderate stakes

### Deep Mode Signals

- User says: "thorough", "comprehensive", "audit", "review"
- Production deployment
- Security-relevant code
- User says: "tear this apart", "stress test"
- High stakes (public API, financial, auth)

---

## Per-Mode Workflow Structure

Each mode needs its own workflow section:

```markdown
## Workflow

### Quick Mode

1. {Fast step 1}
2. {Fast step 2}
3. Report findings

### Standard Mode

1. {Thorough step 1}
2. {Thorough step 2}
3. {Verification step}
4. Report with severity levels

### Deep Mode

1. Context gathering (blocking)
2. {Parallel exploration}
3. {Adversarial review}
4. Synthesis with confidence levels
5. Full report
```

---

## Mode Escalation

Sometimes Claude should escalate mid-skill:

```markdown
## Mode Escalation

Escalate from Quick → Standard if:
- More than 3 issues found
- Security-relevant code detected
- Cross-file dependencies discovered

Escalate from Standard → Deep if:
- Conflicting findings
- User requests more detail
- Critical issues found
```

---

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| No default stated | Add "Default to **X**" |
| Vague criteria ("complex") | Use observable signals |
| Same workflow, different depth | Distinct approaches per mode |
| Missing escalation rules | Define when to upgrade mode |
