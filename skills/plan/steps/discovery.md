---
consumes: [goal]
produces: [discovery-results]
optional: true
---
## Phase 2: Discover

**quick:** Use auggie results from Phase 0. Validate paths exist. No subagent.

**full:** Spawn explorer:
```python
Task(subagent_type="plan-explorer",
     prompt=f"SEARCH for: {description}. RETURN file:line citations, export inventories, importer traces.")
```

For each symbol/file being deleted or renamed: `grep -r 'symbol_name'` across ALL files (skills/, agents/, tests/, hooks/). Every match is in scope or explicitly excluded.

**EXIT CRITERIA:** File paths validated with line numbers. Deleted symbols grepped across full codebase.
