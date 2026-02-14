# Skill Templates

## Simple Tier — Minimal Skill

```markdown
---
name: {skill-name}
description: >-
  {Action verbs} {outputs}. Use when {trigger phrases},
  {file types}, or {contexts}.
---

# {Skill Title}

## Why This Exists

{Problem statement with bullet points:}
- **Pain point 1**: Impact
- **Pain point 2**: Impact

## Quick Start

{Essential example <50 lines}

## Workflow

{Core procedures - keep lean, extract details to references/}

## References

- [detailed-guide.md](references/detailed-guide.md) - Full procedures
```

---

## Simple Tier — Skill with Scripts

```markdown
---
name: processing-{domain}
description: >-
  Processes {domain} files with validated scripts. Use when user
  requests "{action} {domain}", "convert {domain}", or works with
  .{ext} files.
---

# {Domain} Processor

## Why This Exists

{Domain} processing requires deterministic code that gets rewritten each time.
This skill bundles tested scripts for reliable execution.

## Quick Start

```bash
# Most common operation
python3 scripts/{main_script}.py input.{ext} output.{ext}
```

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `{main_script}.py` | {Primary action} | `python3 scripts/{main_script}.py {args}` |
| `{helper}.py` | {Secondary action} | `python3 scripts/{helper}.py {args}` |

## References

- [api-reference.md](references/api-reference.md) - Script parameters
```

---

## Simple Tier — Skill with Domain Knowledge

```markdown
---
name: querying-{system}
description: >-
  Queries {system} with schema awareness. Use when user asks about
  {domain} data, "{system} query", or needs {system} reports.
---

# {System} Query Assistant

## Why This Exists

Querying {system} requires rediscovering schema relationships each time.
This skill bundles schema documentation for accurate queries.

## Quick Start

```sql
-- Example: {common query description}
SELECT {fields}
FROM {table}
WHERE {condition};
```

## Schema Overview

See [schema.md](references/schema.md) for complete table definitions.

**Key tables:**
- `{table1}` - {description}
- `{table2}` - {description}

**Common joins:**
- `{table1}.{fk}` → `{table2}.{pk}`
```

---

## Modal Tier — Skill with 3 Modes

```markdown
---
name: {skill-name}
description: >-
  {Action verbs} {outputs} with adaptive depth. Use when {trigger phrases}.
  Supports Quick (fast), Standard (balanced), Deep (thorough) modes.
---

# {Skill Title}

## Why This Exists

{Problem varies in complexity:}
- **Simple cases**: Need fast resolution
- **Standard cases**: Need balanced depth
- **Complex cases**: Need thorough analysis

This skill adapts approach to task complexity.

## Mode Selection

| Mode | When | Focus |
|------|------|-------|
| **Quick** | {Simple criteria} | {Minimal checks} |
| **Standard** | {Default criteria} | {Balanced approach} |
| **Deep** | {Complex criteria} | {Thorough analysis} |

Default to **Standard**. Use Quick for {trivial signal}. Use Deep when user says "{thorough signal}" or stakes are high.

## Workflow

### Quick Mode

1. {Step 1}
2. {Step 2}
3. Report findings

### Standard Mode

1. {Step 1}
2. {Step 2}
3. {Step 3}
4. {Step 4}
5. Report with severity levels

### Deep Mode

1. All Standard steps
2. {Additional analysis}
3. {Edge case handling}
4. {Verification step}
5. Full report with confidence levels

## Output Format

```markdown
## {Skill} Results

**Mode:** {Quick/Standard/Deep}
**Confidence:** {High/Medium/Low}

### Findings

| # | Severity | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 1 | {P0/P1/P2} | ... | file:line | ... |

### Summary

{2-3 sentence summary}
```

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Using Quick for complex tasks | Check complexity signals first |
| Skipping verification | Always verify before reporting |
| {Domain-specific anti-pattern} | {Fix} |

## References

- [detailed-guide.md](references/detailed-guide.md) - Full procedures per mode
```

---

## Parallel Tier — Skill with Subagents

**Required:** Add `uses_skill_run: true` to frontmatter. Paths auto-injected.

**SKILL.md:**
```markdown
---
name: {skill-name}
description: >-
  {Action verbs} {outputs} using parallel {N} subagents.
  Use when {trigger phrases}. Supports Quick (direct), Standard ({N} agents),
  Deep ({N+2} agents + adversarial) modes.
uses_skill_run: true
---

# {Skill Title}

<!-- Output paths auto-injected by skill_run_initializer:
     - run_dir: ~/projects/{project}/{skill-name}/runs/{date}-{slug}/
     - outputs/: Per-persona findings
     - handoffs/: Per-persona handoffs
     - synthesis: Combined report
     Reference these in your prompts.
-->

## Why This Exists

{Problem benefits from multiple perspectives:}
- **Single-path bias**: First idea becomes only idea
- **Blind spots**: One lens misses issues another catches
- **No prioritization**: Everything flagged, nothing ranked

This skill uses orthogonal {personas/streams} to surface real issues.

## Mode Selection

| Mode | When | Subagents | Output |
|------|------|-----------|--------|
| **Quick** | {Simple criteria} | 0 | Direct response |
| **Standard** | {Default criteria} | {N} | Structured report |
| **Deep** | {Complex criteria} | {N+2} | Full audit + adversarial |

Default to **Standard**. Use Quick for {trivial signal}. Use Deep when user says "{thorough signal}" or stakes are high.

## Workflow

### Phase 1: Context Gathering (BLOCKING)

```python
# Paths from auto-injection (skill_run_initializer):
# - outputs/, handoffs/, context, synthesis (already in your context)

Task(
    subagent_type="Explore",
    model="haiku",
    description="Gather context",
    prompt=f"""## TARGET
{target}

## TASK
Gather context for {skill}. Be FAST (60 seconds).

Research:
1. {Context question 1}
2. {Context question 2}
3. {Context question 3}

## OUTPUT
Write to: {context} (under 300 words)
"""
)
```

**Wait for completion before Phase 2.**

### Phase 2: Write Handoffs

Write {N} handoff files to `{handoffs}/` (path from auto-injection):

```markdown
# {Persona} - Handoff

## Mission
{Persona-specific goal}

## Target
{What to analyze}

## Output Location
{outputs}/{persona}-output.md

## Your Question
"{The ONE question this persona answers}"

## NOT Your Territory (Do NOT flag these)
- {Issue type handled by Persona B}
- {Issue type handled by Persona C}

## Output Limits
- **1 Blocker** - The ONE issue that blocks shipping
- **3 Polish** - Important but shippable
- **3 Skipped** - Considered but not worth flagging

## Tools to Use
{Tool list}
```

### Phase 3: Spawn Subagents (SINGLE MESSAGE)

**CRITICAL: ALL subagents in ONE message:**

```python
Task(subagent_type="general-purpose", description="{Persona A}", run_in_background=True, prompt=...)
Task(subagent_type="general-purpose", description="{Persona B}", run_in_background=True, prompt=...)
Task(subagent_type="general-purpose", description="{Persona C}", run_in_background=True, prompt=...)
```

### Phase 4: Synthesize

Read all output files from `{outputs}/` (path from auto-injection). Apply synthesis algorithm:

1. **Ranking** - Score by mention count (3+ = Critical, 2 = Important, 1 = Supporting)
2. **Confirmation** - Only report findings from 2+ personas
3. **Conflict Detection** - Flag contradictions with both perspectives
4. **Gap Analysis** - What did personas NOT find based on goal?
5. **Confidence** - High (multiple + evidence), Medium (single + evidence), Low (inferred)

### Phase 5: Deliver

```markdown
## {Skill}: {Target}

**Mode:** {Quick/Standard/Deep}
**Verdict:** {APPROVED/FIX_AND_SHIP/REVISE}

### Blockers ({N})

| # | Persona | Issue | Fix | Do NOT |
|---|---------|-------|-----|--------|
| 1 | {Persona A} | ... | ... | ... |

### Polish ({N})

- [{Persona}] {Issue} - {Fix}

### Filtered

- {N} skipped (theoretical, matches existing patterns)
```

## Persona Definitions

| Persona | Question | Territory |
|---------|----------|-----------|
| **{Persona A}** | "What's {X}?" | {Territory A} |
| **{Persona B}** | "What's {Y}?" | {Territory B} |
| **{Persona C}** | "Is this {Z}?" | {Territory C} |

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Sequential subagent launches | MUST be single message with {N} Task calls |
| Overlapping personas | Use "NOT Your Territory" sections |
| No default mode | Explicitly state: "Default to Standard" |
| Vague synthesis | Define algorithm, not "combine results" |
| Missing output limits | Force prioritization with hard caps |

## References

- [persona-prompts.md](references/persona-prompts.md) - Exact prompts for each persona
- [synthesis-template.md](references/synthesis-template.md) - Output format details

## Phase 6: Publish Report

Write final report to `{synthesis}` (path from auto-injection):

```python
# synthesis path already in your context from skill_run_initializer
Write(file_path=synthesis, content=final_report)
```
```
