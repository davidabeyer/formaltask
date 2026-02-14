---
name: creating-agents
description: MUST BE USED when creating Claude Code agents. Activates on "create agent",
  "new agent", "agent best practices", or when building Task subagents.
required_todos:
- discovery-mandatory
---

# Creating Agents

Your job is to create agents that work on first spawn. No hand-holding, no iteration.

## Phase 0: Discovery (MANDATORY)

Before writing anything, clarify with the user:

```python
AskUserQuestion(
    questions=[
        {
            "question": "What specific problem does this agent solve?",
            "header": "Problem",
            "options": [
                {"label": "Code review/audit", "description": "Find bugs, security issues, quality problems"},
                {"label": "Research/exploration", "description": "Search codebase, gather context"},
                {"label": "Implementation", "description": "Write or modify code"},
                {"label": "Verification", "description": "Check claims, validate assumptions"}
            ],
            "multiSelect": False
        },
        {
            "question": "When should this agent be invoked?",
            "header": "Trigger",
            "options": [
                {"label": "After code changes", "description": "Review, test, validate"},
                {"label": "Before implementation", "description": "Plan, research, explore"},
                {"label": "On error/failure", "description": "Debug, diagnose, fix"},
                {"label": "Explicit only", "description": "User must request directly"}
            ],
            "multiSelect": True
        }
    ]
)
```

**Keep asking until you have:**
- Clear problem (not "helps with X")
- Specific trigger phrases
- What success looks like

## Structure

```yaml
---
name: kebab-case-name
description: >
  MUST BE USED when [scenario]. Use PROACTIVELY when [trigger].
  Examples - "[phrase]" → Launch | "[phrase]" → Deploy
tools: [Read, Grep, Glob]  # Minimum needed
model: sonnet              # sonnet|opus|haiku
---

<role>
WHO: [Expert type in 5-10 words]
ATTITUDE: [Sharp stance - what failure looks like, what you won't tolerate]
</role>

<purpose>
Your job is [X]. You do it this way because [Y].
</purpose>

<workflow>
1. [Concrete step]
2. [Concrete step]

## Find the Stupid

| Stupid | Why It's Stupid |
|--------|-----------------|
| [Domain mistake] | [Consequence] |

## Correct Pattern
```[lang]
# THE RIGHT WAY - minimal working code
```
</workflow>

<output>
Format: [prose|table|JSON]
Sections: [what goes where]
Success: [1-line criterion]
</output>

<rules>
- [Constraint]
- [What to NEVER do]
</rules>
```

## Judgment Agents (auditors, reviewers, verifiers)

Add these patterns. Skip for research/implementation agents.

```xml
<meta_analysis>
  <target>[What am I auditing?]</target>
  <bias_check>[What am I predisposed to miss?]</bias_check>
</meta_analysis>

<!-- ... do work ... -->

<checkpoint>
  <verify>[Did I check X?] [YES/NO]</verify>
  <conclusion>VERDICT: [Pass/Fail]</conclusion>
  <flips_if>[Concrete reversal condition]</flips_if>
</checkpoint>
```

**Output limit:** Under 600 words. End with 2-3 actionable next steps.

## Voice Rules

| Wrong | Right |
|-------|-------|
| "This agent reviews code" | "Your job is to catch bugs before they ship" |
| "The purpose is to..." | "You do X because Y" |
| "Consider checking..." | "Check X" |
| "It's recommended to..." | "Do this" |

**Everything is second person. Everything is imperative.**

## Tool Selection

| Agent Type | Tools |
|------------|-------|
| Analysis | Read, Grep, Glob, TodoWrite |
| Implementation | Read, Write, Edit, Bash, Grep, Glob, TodoWrite |
| Review | Read, Grep, Glob, Bash, TodoWrite |

**Hard rules:**
- No `Task/Agent` unless orchestrator
- No 50+ tools
- Include TodoWrite for multi-step work
- Always include `mcp__auggie-mcp__codebase-retrieval` and `mcp__morph-mcp__warpgrep_codebase_search` for code exploration

## Quality Gates

- [ ] Discovery phase completed with user
- [ ] Under 100 lines (50-80 ideal)
- [ ] `<role>` at TOP with WHO + ATTITUDE
- [ ] `<purpose>` uses "Your job is..."
- [ ] Every section uses second person
- [ ] Fresh agent test: executes with ONLY .md file + prompt
- [ ] Antirez test: nothing to mass-delete

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| "This agent does X" | "Your job is X" |
| Generic attitude ("thorough") | Sharp stance ("A bug I miss ships") |
| No Find the Stupid table | Add domain-specific mistakes |
| External file references | Inline or delete |
| Over 100 lines | Cut ruthlessly |
| Documentation tone | Directive tone |

## Fresh Agent Test

Agents receive ONLY their `.md` file + prompt. They don't get:
- Parent conversation
- Other agents' outputs
- Implicit codebase knowledge

**Test:** Can it execute from the `.md` alone? If not, inline what's missing.
