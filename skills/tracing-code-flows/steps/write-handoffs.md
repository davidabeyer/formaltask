---
consumes: [synthesis-report]
produces: [handoff-docs]
---
# Phase 2: Write Handoffs (Full Only)

**Quick mode:** Skip this phase entirely. Trace directly in Phase 5.

**Full mode:** Write handoffs BEFORE spawning subagents. Subagents have zero parent context -- handoffs must be complete and self-contained.

## Entry Point Handoffs

One handoff per entry point:

```python
for i, ep in enumerate(entry_points, 1):
    run.write_handoff(f"entry-point-{i}", f"""# Entry Point: {ep.name}

## Location
{ep.file}:{ep.line}

## Signature
{ep.signature}

## Paths to Trace
- Happy path
- Error conditions
- Edge cases

## Output
{run.outputs}/entry-point-{i}.md
""")
```

## Gap Category Handoffs

One handoff per gap category (categories determined by mode -- see initialize step):

```python
for category in gap_categories:
    run.write_handoff(f"gap-{category}", f"""# Gap Analysis: {category}

## Scope
{files_in_scope}

## Output
{run.outputs}/gap-{category}.md
""")
```

Each handoff must include:
- Exact file scope
- What to analyze
- Where to write output
