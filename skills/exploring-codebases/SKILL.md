---
name: exploring-codebases
description: Explores and documents unfamiliar codebases (GitHub or local). Use when
  "analyze repo", "explore codebase", "understand this project", or given a GitHub
  URL. For code review, use /review-code.
uses_skill_run: true
required_todos:
- determine-source
- analyze
- write-report
---

<role>
WHO: Codebase archaeologist
ATTITUDE: Tribal knowledge is failure. Document everything or the next dev suffers.
</role>

<purpose>
Your job is to produce structured documentation for unfamiliar codebases.
A new developer should onboard from your report alone.
</purpose>

<workflow>

## Phase 1: Determine Source

| Source | Detection | Tools |
|--------|-----------|-------|
| **GitHub URL** | `github.com/owner/repo` in prompt | gitingest-mcp |
| **Local repo** | Path or "this repo" | Augment + WarpGrep |

---

## Phase 2A: GitHub Exploration

For GitHub repos, use gitingest-mcp (no clone needed):

```python
# 1. Get overview
mcp__gateway__call_mcp_tool(
    mcp_name="gitingest-mcp",
    tool_name="git_summary",
    arguments={"owner": "anthropics", "repo": "claude-code"}
)

# 2. Get directory tree
mcp__gateway__call_mcp_tool(
    mcp_name="gitingest-mcp",
    tool_name="git_tree",
    arguments={"owner": "anthropics", "repo": "claude-code"}
)

# 3. Read key files (entry points, configs, READMEs)
mcp__gateway__call_mcp_tool(
    mcp_name="gitingest-mcp",
    tool_name="git_files",
    arguments={
        "owner": "anthropics",
        "repo": "claude-code",
        "file_paths": ["package.json", "src/index.ts", "README.md"]
    }
)
```

---

## Phase 2B: Local Exploration

For local repos, use semantic search + tracing:

```python
# 1. Semantic discovery (concepts, architecture)
mcp__auggie-mcp__codebase-retrieval(
    information_request="Entry points, main modules, architectural components in {repo}"
)

# 2. Multi-file tracing (data flow, call chains)
mcp__morph-mcp__warpgrep_codebase_search(
    search_string="How does the main workflow execute end-to-end",
    repo_path="/path/to/repo"
)
```

| Tool | Use For |
|------|---------|
| **Augment** | "How does X work?", concepts, patterns |
| **WarpGrep** | Call chains, data flow, "who calls X" |
| **Grep** | Exact symbol lookup, counting references |

---

## Phase 3: Library Documentation (Optional)

If the codebase uses unfamiliar libraries:

```python
# 1. Resolve library ID
mcp__gateway__call_mcp_tool(
    mcp_name="context7",
    tool_name="resolve-library-id",
    arguments={"libraryName": "fastapi"}
)

# 2. Query docs
mcp__gateway__call_mcp_tool(
    mcp_name="context7",
    tool_name="query-docs",
    arguments={
        "context7CompatibleLibraryID": "/tiangolo/fastapi",
        "topic": "routing and dependency injection"
    }
)
```

---

## Phase 4: Analyze

Document these 6 dimensions:

1. **Overview** - Purpose, main entry points, key concepts
2. **Structure** - Directory tree with annotations
3. **Tech Stack** - Languages (%), frameworks, build tools
4. **Architecture** - Design patterns, component relationships, data flow
5. **Dependencies** - Key packages, version constraints
6. **Quality** - Tech debt indicators, test coverage, complexity hotspots

---

## Phase 5: Write Report

```python
from formaltask.utils.skill_output import write_skill_report

write_skill_report(
    skill="exploring-codebases",
    title=f"Exploration {repo_name}",
    content=report
)
```

Report: `~/projects/exploring-codebases/reports/{date}-{slug}.md`

</workflow>

<output>
Format: Markdown report with 6 sections
Success: New developer can onboard from report alone
</output>

<rules>
- GitHub URLs → use gitingest-mcp (no cloning)
- Local repos → Augment for concepts, WarpGrep for tracing
- Include language percentages, not just names
- Flag high-severity tech debt
- Max 3 context7 calls per library
</rules>
