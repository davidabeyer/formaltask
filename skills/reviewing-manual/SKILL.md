---
name: reviewing-manual
description: Context-aware code review with dynamic reviewer selection. Use when "/review",
  "review this", "check my work", or after implementing. For auto-spawned reviews,
  use reviewing-code instead.
uses_skill_run: true
---

<role>
WHO: Review orchestrator who matches work to experts
ATTITUDE: Generic reviews miss domain bugs. Targeted reviews catch them.
</role>

<purpose>
Your job is to look at what you just did, pick the right reviewers, and craft prompts they can execute cold. Spawned agents know NOTHING about this conversation—your prompt is their entire world.
</purpose>

## Philosophy

**Antirez standard:** Simple > Complete. Delete > Add. 10 lines > 100 lines.
**Beck's Razor:** Would deleting this test let a real bug slip through? No → delete it.

Every reviewer judges against these standards.

## Available Reviewers

| Reviewer | Domain |
|----------|--------|
| code-reviewer | General quality, simplicity, antirez-style |
| sqlite-reviewer | Transactions, SQL injection, migrations |
| error-handling-reviewer | Exception handling, logging, visibility |
| api-client-reviewer | External APIs, rate limits, retries |
| path-security-reviewer | File paths, traversal, permissions |
| subprocess-reviewer | Shell commands, process lifecycle |
| state-machine-reviewer | State transitions, idempotency |
| schema-reviewer | Pydantic, validation, serialization |
| tui-reviewer | Textual widgets, reactive bindings |
| hook-reviewer | PreToolUse validators, guards |
| test-quality-auditor | Test legitimacy, Beck's Razor |
| performance-auditor | N+1, complexity, resource leaks |
| critique-security-auditor | Auth, injection, OWASP |
| critique-antirez-reviewer | Over-engineering, deletion candidates |

## Workflow

1. **Consider recent work** - What did you just write/modify? What domains does it touch?

2. **Recommend 3-4 reviewers** - Pick from the table. Always include `code-reviewer`. Present via AskUserQuestion with multiSelect.

3. **Craft complete prompts** - Spawned agents are AMNESIACS. Include:

```
## WHAT YOU'RE REVIEWING
[Exact file paths with line ranges if relevant]

## WHAT WAS DONE
[Summarize the work: "Added error handling to database connection pool"]

## WHY IT WAS DONE
[The goal: "Prevent silent failures when PostgreSQL is unreachable"]

## YOUR FOCUS
[Domain-specific concerns for THIS reviewer]

## STANDARDS
- Antirez: Can anything be deleted? Is this the simplest solution?
- Beck's Razor (for tests): Would removing this test let a real bug slip?

## OUTPUT
Write to: {outputs}/{reviewer}.md

Format:
# {reviewer} Findings

## P0 (Blockers) - Would refuse to ship
[file:line - issue - fix]

## P1 (High) - Should fix before merge
[file:line - issue - fix]

## Delete This
[Code that should be removed, abstractions to flatten, tests to delete]

## Verdict: [APPROVED | NEEDS_FIXES | BLOCKED]
```

4. **Spawn in SINGLE message** - All reviewers launch in parallel.

5. **Synthesize** - Read `{outputs}/*.md`, aggregate by severity, write `{synthesis}/review-summary.md`.

<rules>
- Prompts must be executable by an amnesiac agent
- Every prompt includes the antirez + Beck standards
- Spawn all reviewers in ONE message
- P0 from ANY reviewer = overall BLOCKED
</rules>
