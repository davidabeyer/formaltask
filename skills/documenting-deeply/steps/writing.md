---
consumes: [doc-gaps]
produces: [doc-drafts]
---
# Phase 5: Documentation Writing (Subagent)

Write documentation based on deep comprehension.

## Subagent

```python
Task(
    subagent_type="general-purpose",
    description=f"Write documentation for {area}",
    prompt=f"""
PHASE 5: DOCUMENTATION WRITING

WORKING DIR: {run.run_dir}

Read these files:
- Comprehension: {run.run_dir}/03-comprehension.md
- Gap analysis: {run.run_dir}/04-gap-analysis.md
- Doc patterns: {run.run_dir}/../references/doc-patterns.md

TASKS:
1. Write README.md content for the target area
2. Write CLAUDE.md content (terse, links to README)
3. Follow existing documentation style
4. Include code examples that actually work

STYLE REQUIREMENTS:
- README.md: Comprehensive, examples, rationale
- CLAUDE.md: Terse tables, quick reference, links out

WRITE TO:
- {run.run_dir}/05-readme-draft.md
- {run.run_dir}/05-claudemd-draft.md

Include markers for where content goes in existing files if updating.
"""
)
```

See [doc-patterns.md](../references/doc-patterns.md) for format guidelines.
