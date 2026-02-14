# Tool Selection Guidelines

**Principle**: Grant minimum necessary permissions. Bloated tool lists increase attack surface and confusion.

## Core Tools by Agent Type

| Agent Type | Core Tools | Add TodoWrite? |
|------------|------------|----------------|
| Analysis/Research | Read, Grep, Glob, WebSearch, WebFetch | Yes (multi-step) |
| Implementation | Read, Write, Edit, Bash, Grep, Glob | Yes (multi-step) |
| Quality/Review | Read, Grep, Glob, Bash | Yes (multi-aspect) |
| Verification | Read, Grep, Glob, Bash | Yes (multi-criteria) |
| Simple/Single-shot | Read, Grep, Glob | No (one action) |

## TodoWrite: Include by Default for Complex Work

Per Anthropic guidance: "Surface agent planning steps explicitly."

**Include TodoWrite when:**
- Agent has multi-step workflow (most agents)
- Multiple criteria/aspects to evaluate
- Systematic investigation or iteration
- User benefits from progress visibility

**Exclude TodoWrite only when:**
- Truly single-action agent (parse, format, convert)
- Agent produces output in one shot without phases

## Security-Critical Restrictions

| Tool | Risk | Guidance |
|------|------|----------|
| `Task`, `Agent` | Recursive spawning | Only in orchestration agents |
| `Bash` | Command execution | Include only when needed |
| `Write`, `Edit` | File modification | Include only for implementation |
| MCP tools | Scope creep | Limit to specifically needed |

**Hard rule**: Never 50+ tools (bloat indicates unclear purpose)
