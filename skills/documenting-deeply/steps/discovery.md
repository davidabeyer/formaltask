---
consumes: [doc-verdict]
produces: [doc-map]
---
# Phase 1: Documentation Discovery (Subagent)

Map existing documentation architecture before making changes.

## Subagent

```python
Task(
    subagent_type="Explore",
    description="Map documentation architecture",
    prompt=f"""<doc_discovery>
  <role>Documentation archaeologist mapping existing structure</role>
  <goal>Complete map of existing docs before making changes</goal>
  <why>Can't improve what you haven't surveyed</why>
  <context>
    <target>{target_path}</target>
  </context>
  <tasks>
    1. Find all README.md and CLAUDE.md files
    2. Identify documentation pattern (flat, hierarchical, mixed)
    3. Map coverage: which directories have docs vs don't
    4. Note cross-references between docs
  </tasks>
  <output>
    <location>{run.run_dir}/01-doc-discovery.md</location>
    <format>Coverage table + pattern description + observations</format>
  </output>
  <avoid>Evaluating quality yet - just map what exists</avoid>
</doc_discovery>"""
)
```
