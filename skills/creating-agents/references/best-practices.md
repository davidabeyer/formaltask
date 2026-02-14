# Agent Best Practices

Based on Anthropic's "Building Effective Agents" research and prompt optimization guidance.

## Core Principles

### 1. Start Simple (antirez Style)

**Target: 50-100 lines.** If longer, you're over-engineering.

Ask yourself: "Would antirez mass-delete half of this?" If yes, do it yourself.

| antirez would delete | Keep instead |
|---------------------|--------------|
| Abstract factories | Direct function calls |
| Config options nobody uses | Hardcoded sensible defaults |
| Wrapper functions | Inline the logic |
| "Flexibility" for imagined futures | Solve today's problem |

### 2. Explicit Role (Dramatically Improves Quality)

Put `<role>` block at the TOP, not buried in prose.

```markdown
<!-- BAD: Buried in prose -->
You are an expert code reviewer with deep expertise in...

<!-- GOOD: Explicit and first -->
<role>
WHO: Expert code reviewer with architecture depth
ATTITUDE: Thorough but pragmatic - real issues, not nitpicks
</role>
```

### 3. WHY, Not Just WHAT

Every agent needs a `<purpose>` explaining WHY this approach.

```markdown
<!-- BAD: Just describes what -->
<purpose>
Perform comprehensive code reviews.
</purpose>

<!-- GOOD: Explains why this approach -->
<purpose>
Systematic review catches bugs that ad-hoc reading misses.
By examining security, performance, and architecture in sequence,
we ensure nothing slips through.
</purpose>
```

### 4. Structured Output (Format/Sections/Length/Success)

Vague output specs produce vague outputs.

```markdown
<!-- BAD: Vague -->
<output_format>
Provide a comprehensive review with recommendations.
</output_format>

<!-- GOOD: Specific -->
<output>
Format: Structured markdown
Sections:
  - Summary: [2-3 sentences]
  - Critical Issues: [Blockers with file:line]
  - Recommendations: [Prioritized actions]
Length: Under 100 lines
Success: All issues have citations and suggested fixes
</output>
```

### 5. Fresh Agent Test

Agents receive ONLY their `.md` file + prompt parameter. They don't see:
- Parent conversation history
- Other agents' outputs (unless passed in prompt)
- Implicit codebase knowledge

**Test:** Can the agent execute with ONLY `Task(subagent_type="X", prompt="do Y")`?

**Violations:**
- "See agents/shared/X.md" → Inline the content
- Assumes parent context → Make self-contained
- References prior conversation → Pass info in prompt

### 6. Single Responsibility

Each agent does ONE thing well. If you need multiple capabilities:
- Break into separate agents
- Use orchestrator-worker pattern

### 7. Environmental Feedback

Agents should use tool results to guide decisions, not assume.

```markdown
<workflow>
1. Run diagnostic command
2. Analyze output for patterns
3. Form hypothesis based on evidence
4. Test hypothesis with targeted action
5. Verify fix resolves issue
</workflow>
```

## Anti-Over-Engineering Checklist

Before finalizing, verify:

- [ ] **Under 100 lines** (50-80 ideal)
- [ ] **No verbose examples** - Agent knows how to code
- [ ] **No JSON protocol templates** - Agent knows JSON
- [ ] **No "Remember:" sections** - Put it in rules if it matters
- [ ] **No duplicate content** - Each idea appears once
- [ ] **No external file references** - Fresh agent test
- [ ] **antirez test passes** - Nothing to mass-delete

## What to Delete

| Delete This | Why |
|-------------|-----|
| 50+ line code examples | Agent knows the language |
| JSON communication protocols | Agent knows JSON |
| Verbose methodology descriptions | Workflow phases are enough |
| "Remember:" and motivational sections | Either it's in rules or it doesn't matter |
| Duplicate explanations | Say it once |
| External file references | Fails fresh agent test |

## References

- Anthropic: [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- Claude Docs: [Claude 4 Best Practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)
- Claude Docs: [Use XML Tags](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags)
