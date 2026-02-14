# FormalTask Path Conventions

Standard paths for FormalTask planning artifacts. Agents receive these paths when invoked.

## Path Structure

| Resource | Path Pattern |
|----------|-------------|
| Plans root | `~/projects/{project}/plans/` |
| Specs directory | `~/projects/{project}/plans/specs/` |
| Epic file | `~/projects/{project}/plans/epics/{project}/epic.md` |
| Plan versions | `~/projects/{project}/plans/{project}-v{N}.md` |
| Database | `.claude/formaltask.db` (after /epic-decompose) |

## CLI Queries

```bash
# List tasks for an epic
python3 -m formaltask.cli.pm task-list {project_name}

# Show task details (includes depends_on, spec content)
python3 -m formaltask.cli.pm task-show {task_id}

# Find plan v1 (original intent)
ls ~/projects/{project}/plans/{project}-v*.md | head -1
```

## Notes

- Paths are typically passed explicitly when agents are invoked
- Use `project_name` to derive paths only as fallback
- Database queries require `/epic-decompose` to have run first

## MCP Tool Fallback Strategy

If MCP gateway tools are unavailable or fail:

| Primary Tool | Fallback | Use Case |
|--------------|----------|----------|
| auggie-mcp codebase-retrieval | Grep + Read | Semantic → exact pattern search |
| morph-mcp warpgrep | Grep with `-C` context | Multi-file traces |
| context7 library docs | WebSearch + WebFetch | Library documentation |

**Detection:** If MCP tools return errors or empty results, fall back to native tools.

**Example fallback workflow:**
```python
# Try direct MCP first
result = mcp__auggie-mcp__codebase-retrieval(information_request="...")

# If fails or returns nothing useful, fall back
if not result or "error" in result:
    # Use Grep for exact symbol search
    Grep(pattern="def {function_name}", glob="*.py")
    # Use Read for context around matches
    Read(file_path=matched_file, offset=line-5, limit=20)
```
