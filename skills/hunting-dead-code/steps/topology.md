---
consumes: [hunt-target]
produces: [code-topology]
---

# Phase 1: Code Topology Mapping

**quick:** Skip subagent. Use auggie + warpgrep directly to map entry points and orphan candidates. Report findings inline.

**full:** Spawn topology mapper subagent:

Before deleting code, understand the call graph.

```python
run.write_log("Starting code topology mapping", phase="Phase 1")

Task(
    subagent_type="Explore",
    description="Map code topology",
    prompt=f"""<topology_mapper>
  <role>Code archaeologist mapping the call graph before any deletion</role>
  <goal>Complete topology map identifying orphan candidates</goal>
  <why>Can't safely delete what you don't understand</why>
  <context><target>{target_path}</target></context>
  <tasks>
    1. Module inventory (packages, entry points, public API)
    2. Import graph (what imports what, circular deps)
    3. Call graph sketch (major chains, orphan candidates)
    4. Dynamic patterns (getattr, plugins, decorators) - CAUTION ZONES
    5. Test coverage (what's tested, what's not)
  </tasks>
  <output>
    <location>{run.run_dir}/01-code-topology.md</location>
    <format>Entry points table, dependency graph, orphan candidates, dynamic patterns</format>
  </output>
  <avoid>Making deletion recommendations yet - just map</avoid>
</topology_mapper>"""
)
```

**Wait for completion. Read and internalize the mapping.**

```python
run.write_log("Topology mapping complete", phase="Phase 1")
```
