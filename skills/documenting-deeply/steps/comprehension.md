---
consumes: [doc-map]
produces: [code-understanding]
---
# Phase 3: Deep Comprehension (Subagent)

Understand the code BEFORE writing any documentation.

## Subagent

```python
Task(
    subagent_type="general-purpose",
    description=f"Deep comprehension of {area}",
    prompt=f"""
PHASE 3: DEEP COMPREHENSION

TARGET: {area_path}
WORKING DIR: {run.run_dir}

Your job: Build complete understanding of this code before documenting it.
DO NOT WRITE DOCUMENTATION YET. Only understand.

Read the comprehension protocol: {run.run_dir}/../references/comprehension-phase.md

TASKS:
1. Read ALL files in the target area (not just entry points)
2. Trace 3-5 representative execution paths
3. Identify the design intent and patterns
4. Note edge cases and special behaviors
5. Find WHY decisions were made (git blame, comments)

COMPREHENSION CHECKPOINT - Answer these BEFORE proceeding:
1. What problem does this code solve?
2. How does it solve it? (mechanism)
3. What are the key abstractions?
4. What are the edge cases?
5. What would surprise a reader?

WRITE TO: {run.run_dir}/03-comprehension.md

If you cannot answer all five questions, continue reading. Do not proceed.
"""
)
```

See [comprehension-phase.md](../references/comprehension-phase.md) for detailed protocol.
