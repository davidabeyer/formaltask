# Parallel Orchestration Patterns

For skills that benefit from multiple perspectives, parallel subagent orchestration provides breadth without sequential context exhaustion.

## Why Parallel Matters

Sequential exploration:
- Exhausts context on first path
- First idea becomes only idea
- Later exploration is shallow

Parallel exploration:
- Equal depth across all paths
- Surfaces contradictions
- Enables synthesis across perspectives

---

## Phase-Gated Execution

All parallel skills follow this structure:

```
Phase 0: Context Gathering (BLOCKING)
    ↓ Wait for completion
Phase 1: Write Handoffs
    ↓
Phase 2: Spawn Subagents (SINGLE MESSAGE)
    ↓ Wait for all to complete
Phase 3: Synthesize Results
    ↓
Phase 4: Deliver Output
```

### Why Blocking Gates?

**Phase 0 blocks Phase 1:** Subagents need context to do useful work. Without shared context, they'll gather redundant information.

**Phase 2 blocks Phase 3:** Synthesis requires all outputs. Partial synthesis produces incomplete results.

---

## The Single-Message Rule

**CRITICAL:** All subagents MUST be spawned in a SINGLE message.

**Bad (sequential):**
```python
# Message 1
Task(description="Agent 1", ...)

# Message 2
Task(description="Agent 2", ...)

# Message 3
Task(description="Agent 3", ...)
```

**Good (parallel):**
```python
# Single message with all 3
Task(description="Agent 1", run_in_background=True, ...)
Task(description="Agent 2", run_in_background=True, ...)
Task(description="Agent 3", run_in_background=True, ...)
```

Sequential spawning:
- Agents run serially
- Earlier results influence later prompts
- Defeats the purpose of parallel exploration

---

## Handoff File Pattern

Subagents need explicit handoffs, not inline prompts.

### Handoff Structure

```markdown
# {Persona Name} - Handoff

## Mission
{One-sentence goal for this persona}

## Context
Read: {run_dir}/context.md

## Target
{Specific thing to analyze}

## Your Question
"{The ONE question this persona answers}"

## NOT Your Territory (Do NOT flag these)
- {Issue type 1 - handled by another persona}
- {Issue type 2 - handled by another persona}

## Output Location
{run_dir}/outputs/{persona}-output.md

## Output Limits
- **1 Blocker** - The ONE issue that blocks shipping
- **3 Polish** - Important but shippable
- **3 Skipped** - Considered but not worth flagging

## Output Format
{JSON or markdown structure expected}

## Tools to Use
- {Tool 1} for {purpose}
- {Tool 2} for {purpose}
```

### Why Files Instead of Inline Prompts?

1. **Readable:** Can inspect handoffs before spawning
2. **Debuggable:** Can see exactly what each agent received
3. **Reusable:** Same handoff template across invocations
4. **Auditable:** Post-hoc analysis of what went wrong

---

## Subagent Prompt Template

```python
Task(
    subagent_type="general-purpose",
    description=f"{persona_name}",
    run_in_background=True,
    prompt=f"""You are the {persona_name} for {skill_name}.

1. Read your handoff: {handoff_path}
2. Read shared context: {context_path}
3. Execute your mission using specified tools
4. Write findings to: {output_path}

Rules:
- Stay within your territory
- Respect output limits (1 blocker max)
- Include file:line evidence
- Write structured output per format spec
"""
)
```

---

## Output Directory Structure

```
{run_dir}/
├── context.md              # Shared context (Phase 0)
├── handoffs/
│   ├── persona-a.md        # Handoff for Persona A
│   ├── persona-b.md        # Handoff for Persona B
│   └── persona-c.md        # Handoff for Persona C
├── outputs/
│   ├── persona-a-output.md # Output from Persona A
│   ├── persona-b-output.md # Output from Persona B
│   └── persona-c-output.md # Output from Persona C
└── synthesis.md            # Final synthesized report
```

---

## Failure Handling

### Subagent Timeout

```markdown
## Failure Handling

If subagent times out:
1. Log which agent failed
2. Continue with available outputs
3. Note incomplete coverage in synthesis
4. Reduce confidence score accordingly
```

### All Subagents Fail

```markdown
If all subagents fail:
1. Fall back to Quick mode (direct analysis)
2. Report degraded mode to user
3. Offer to retry with different approach
```

### Contradictory Results

```markdown
If subagents contradict:
1. Flag contradiction explicitly
2. Present both perspectives with evidence
3. Note which has stronger evidence
4. Let user decide (don't auto-resolve)
```

---

## Scaling Subagent Count

| Complexity | Subagents | Structure |
|------------|-----------|-----------|
| Standard | 3 | Core perspectives |
| Deep | 5 | Core + Adversarial + Perspective |
| Ultrathink | 6+ | Core + Adversarial + Multiple specialists |

### When to Add More Subagents

- **Adversarial:** When stakes are high, add a challenger
- **Perspective:** When multiple stakeholders, add their views
- **Specialist:** When domain expertise needed, add domain agent

---

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Sequential spawning | MUST be single message |
| Inline prompts | Write handoff files |
| No shared context | Phase 0 creates context.md |
| No output limits | Each persona: 1 blocker max |
| Partial synthesis | Wait for ALL outputs |
| Auto-resolving contradictions | Flag and present both |
