---
consumes: [audit-mode]
produces: [architecture-map]
optional: true
---
# Phase 1: Architecture Mapping (full only)

**quick:** Skip this phase. Use auggie + warpgrep directly in Phase 1-Single.

**full:** Spawn context-priming-auditor to deeply understand the system:

```python
Task(
    subagent_type="context-priming-auditor",
    description="Map architecture",
    prompt=f"""## TARGET
{target_path}

## OUTPUT
{run_dir}/outputs/01-architecture-mapping.md

## TASK
ARCHITECTURE MAPPING for deep code audit.

1. Read EVERY file in target - no skimming
2. Identify all modules and responsibilities
3. Map data flow through the system
4. Trace 3-5 representative execution paths with file:line refs
5. Document design philosophy (inferred from patterns)
6. Note key abstractions and justify which are earned

See references/subagent-prompts.md#phase-1 for output format."""
)
```

Wait for completion. Read handoff.
