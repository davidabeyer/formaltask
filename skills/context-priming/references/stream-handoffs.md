# Stream Handoff Templates

Consolidated handoffs for Standard (3 streams) and Deep (5 streams) modes.

---

## Standard Mode Streams

### Stream 1: Docs + Semantic

```markdown
# Stream 1: Docs + Semantic - Handoff

## Mission
Discover project documentation and semantic code context for the target area.

## Target Area
{target_path}

## Project Root
{project_root}

## Goal Context
{goal: debugging/feature/refactoring/understanding}

## Output Location
{output_dir}/outputs/stream-1-output.md

## Discovery Checklist

### Documentation
- [ ] Glob `**/CLAUDE.md` filtering to path hierarchy
- [ ] Read root CLAUDE.md
- [ ] Read intermediate CLAUDE.md files (parent directories)
- [ ] Read target area CLAUDE.md (if exists)
- [ ] Extract: tech stack, patterns, gotchas, testing requirements
- [ ] Note project-wide vs area-specific rules

### Semantic Search
- [ ] codebase-retrieval: "Core implementation of {target}, key classes, entry points"
- [ ] codebase-retrieval: "Error handling and validation in {target}"
- [ ] Identify: entry points, public API, internal helpers

## Tools
- Glob: `**/CLAUDE.md`
- Read: Each CLAUDE.md in hierarchy
- codebase-retrieval: 2-3 semantic queries

## Output Format
See references/output-format.md
```

---

### Stream 2: Flow + Pattern

```markdown
# Stream 2: Flow + Pattern - Handoff

## Mission
Trace multi-file flows and discover code patterns/symbols in the target area.

## Target Area
{target_path}

## Project Root
{project_root}

## Goal Context
{goal: debugging/feature/refactoring/understanding}

## Output Location
{output_dir}/outputs/stream-2-output.md

## Discovery Checklist

### Flow Tracing
- [ ] warpgrep: "How does {target} work end-to-end"
- [ ] warpgrep: "Data flow through {target}"
- [ ] warpgrep: "How {target} integrates with rest of system"
- [ ] Note: integration points, data transformations, error paths

### Pattern Discovery
- [ ] Grep: `class\s+\w+` in target (all classes)
- [ ] Grep: `def (validate|process|handle|create|update|delete)` (key functions)
- [ ] Grep: `TODO|FIXME|HACK` (technical debt)
- [ ] Grep: `^[A-Z][A-Z_]+ =` (constants)
- [ ] Note: naming conventions, organization patterns

## Tools
- warpgrep: 2-3 flow queries
- Grep: 4-5 pattern searches

## Output Format
See references/output-format.md
```

---

### Stream 3: Test + History

```markdown
# Stream 3: Test + History - Handoff

## Mission
Discover test coverage, usage patterns, git history, and dependencies for the target area.

## Target Area
{target_path}

## Project Root
{project_root}

## Goal Context
{goal: debugging/feature/refactoring/understanding}

## Output Location
{output_dir}/outputs/stream-3-output.md

## Discovery Checklist

### Test Discovery
- [ ] Glob: `**/*test*.py` or `**/*.test.*` in/near target
- [ ] Read: 2-3 representative test files
- [ ] Extract: usage patterns, edge cases, expected behaviors
- [ ] Note: what's well-tested vs gaps

### Git History
- [ ] Bash: `git log --oneline -15 -- {target}`
- [ ] Bash: `git log --oneline --since="2 weeks ago" -- {target}`
- [ ] Note: recent changes, active development, bug fixes

### Dependencies
- [ ] Grep: `from {module} import` (who uses this?)
- [ ] Read imports in target files (what does this use?)
- [ ] Note: blast radius for changes

## Tools
- Glob: Test file patterns
- Read: Test files
- Bash: git log commands
- Grep: Import patterns

## Output Format
See references/output-format.md
```

---

## Deep Mode Additional Streams

### Stream 4: Semantic (Dedicated)

```markdown
# Stream 4: Semantic - Handoff

## Mission
Deep semantic code discovery focused on implementation details.

## Target Area
{target_path}

## Project Root
{project_root}

## Goal Context
{goal: debugging/feature/refactoring/understanding}

## Output Location
{output_dir}/outputs/stream-4-output.md

## Discovery Checklist
- [ ] codebase-retrieval: "Core implementation of {target}, main classes and their responsibilities"
- [ ] codebase-retrieval: "Error handling, validation, and edge cases in {target}"
- [ ] codebase-retrieval: "Configuration, constants, and defaults in {target}"
- [ ] codebase-retrieval: "Public API vs internal helpers in {target}"
- [ ] Identify: entry points, extension points, hot paths

## Tools
- codebase-retrieval: 4-5 focused queries

## Output Format
See references/output-format.md
```

---

### Stream 5: Pattern (Dedicated)

```markdown
# Stream 5: Pattern - Handoff

## Mission
Exhaustive symbol and pattern discovery for the target area.

## Target Area
{target_path}

## Project Root
{project_root}

## Goal Context
{goal: debugging/feature/refactoring/understanding}

## Output Location
{output_dir}/outputs/stream-5-output.md

## Discovery Checklist
- [ ] Grep: `class\s+\w+` (all class definitions)
- [ ] Grep: `def\s+\w+` (all function definitions)
- [ ] Grep: `async def` (async functions)
- [ ] Grep: `^[A-Z][A-Z_]+ =` (constants)
- [ ] Grep: `raise\s+\w+` (exception types)
- [ ] Grep: `@\w+` (decorators used)
- [ ] Analyze: naming conventions, code organization
- [ ] Note: patterns, anti-patterns, technical debt

## Tools
- Grep: 6-8 pattern searches with files_with_matches and content modes

## Output Format
See references/output-format.md
```

---

## Subagent Spawn Prompt

Use this template when spawning subagents:

```
You are a discovery subagent for context priming.

## Instructions
1. Read the handoff file at: {handoff_path}
2. Execute all checklist items using specified tools
3. Write findings to: {output_path}

## Rules
- Focus ONLY on your stream's scope
- Include file:line locations for all findings
- Capture patterns, not just individual instances
- Be thorough within scope, skip nothing in checklist
- Write structured output following the format spec

## Tools Available
{stream-specific tool list}

## Success Criteria
- All checklist items completed
- Each finding has location + purpose + relevance
- Actionable takeaways provided
- Output written to correct location
```
