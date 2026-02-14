# Agent Body Structure

**Target: 50-100 lines.** Over-engineering is the enemy.

## Template

```markdown
<role>
WHO: [Expert type, 5-10 words]
ATTITUDE: [How they approach work - skeptical, thorough, pragmatic, etc.]
</role>

<purpose>
WHY this agent exists and WHY this approach (not alternatives).
1-2 sentences max.
</purpose>

<workflow>
## Phase 1: [Name]
1. [Concrete step with tool usage]
2. [Concrete step]

## Phase 2: [Name]
1. [Concrete step]
2. [Concrete step]
</workflow>

<output>
Format: [prose | table | checklist | JSON | code]
Sections:
  - [Section 1]: [what goes here]
  - [Section 2]: [what goes here]
Length: [constraint, or "as needed"]
Success: [1-line measurable criterion]
</output>

<rules>
- [Constraint 1]
- [Constraint 2]
- [What to NEVER do]
</rules>
```

## Required Sections

| Section | Purpose | Notes |
|---------|---------|-------|
| `<role>` | WHO + ATTITUDE at top | Dramatically improves output quality |
| `<purpose>` | WHY this approach | Not just what - justify the method |
| `<workflow>` | Numbered execution phases | Concrete steps, not vague descriptions |
| `<output>` | Format/Sections/Length/Success | Specific structure, measurable success |
| `<rules>` | Constraints and never-do | Include anti-over-engineering if relevant |

## Removed Sections

| Old Section | Why Removed |
|-------------|-------------|
| `<responsibilities>` | Redundant with workflow |
| Verbose examples | Agent knows how to code |
| JSON protocol templates | Agent knows JSON |
| "Remember:" sections | Put it in rules if it matters |

## Anti-Patterns

| Wrong | Right |
|-------|-------|
| Role buried in prose: "You are an expert..." | `<role>` block at TOP |
| `<output_format>[Specify format]</output_format>` | Explicit Format/Sections/Length/Success |
| 50+ line example code blocks | Trust the agent, keep examples minimal |
| References to external files | Inline critical content (fresh agent test) |
