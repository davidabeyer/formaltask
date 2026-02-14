# Stream Output Format

All discovery subagents write output in this format for consistent synthesis.

---

## Required Structure

```markdown
# Stream {N}: {Name} - Findings

**Target:** {target area path}
**Goal:** {debugging/feature/refactoring/understanding}
**Completed:** {ISO 8601 timestamp}

## Summary
{2-3 sentences: what was discovered, key counts}

## Findings

### {Category}

**{Item Name}**
- **Location:** `file:line`
- **Purpose:** What it does
- **Relevance:** Why it matters for {goal}

### {Category 2}
...

## Key Files

| File | Purpose | Priority |
|------|---------|----------|
| `path:line` | Brief description | High/Med/Low |

Priority:
- High = Essential for understanding
- Medium = Useful context
- Low = Peripheral

## Patterns

| Pattern | Locations | Implication |
|---------|-----------|-------------|
| {name} | {where} | {what it means} |

## Takeaways

- {Actionable insight 1}
- {Actionable insight 2}
- {Actionable insight 3}

## Gaps

{What wasn't found that might be needed}
```

---

## Field Guidelines

### Summary
- 2-3 sentences max
- Include counts: "Found 3 CLAUDE.md files, 12 classes, 45 functions"
- Focus on most important discoveries

### Findings
- Group by logical category
- Every item needs: Location, Purpose, Relevance
- Use `file:line` format, not vague references

### Key Files
- Limit to 10-15 most relevant
- Always include priority
- High priority = orchestrator should read this

### Patterns
- Name recognizable patterns (Factory, State Machine, etc.)
- Note where they appear
- Explain implications for the goal

### Takeaways
- 3-5 bullets
- Actionable, not repetitive
- Synthesis, not summary

### Gaps
- Honest about what wasn't found
- Helps orchestrator know what to supplement
