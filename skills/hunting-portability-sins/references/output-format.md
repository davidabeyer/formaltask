# Lens Output Format

All lens subagents write findings as JSON to enable aggregation and report generation.

## JSON Schema

```json
{
  "lens": {
    "number": 1,
    "name": "Path Hardcoding",
    "timestamp": "2025-01-19T10:00:00Z"
  },
  "summary": {
    "total_findings": 8,
    "by_severity": {
      "blocker": 2,
      "warning": 4,
      "note": 2
    },
    "grade": "C",
    "portability_score": 2.5,
    "key_insight": "All paths derive from hardcoded /home/user/cc base"
  },
  "blockers": [
    {
      "id": "L1-B001",
      "title": "Hardcoded database path",
      "category": "user_path",
      "location": {
        "file": "hooks/lib/db_connection.py",
        "line": 23,
        "symbol": "get_db_path"
      },
      "evidence": "db_path = \"/home/user/cc/.claude/formaltask.db\"",
      "impact": "Fails immediately on any other machine",
      "fix": {
        "pattern": "Use PROJECT_ROOT env var",
        "code_before": "db_path = \"/home/user/cc/.claude/formaltask.db\"",
        "code_after": "db_path = Path(os.environ.get(\"PROJECT_ROOT\", \".\")) / \".claude\" / \"formaltask.db\""
      },
      "effort": "low"
    }
  ],
  "warnings": [
    {
      "id": "L1-W001",
      "title": "Relative path assumes CWD",
      "category": "cwd_assumption",
      "location": {"file": "hooks/cli/pm.py", "line": 45},
      "evidence": "config_path = Path(\".claude/config.json\")",
      "impact": "Fails if run from different directory",
      "fix": {
        "pattern": "Anchor to __file__ or PROJECT_ROOT"
      },
      "effort": "low"
    }
  ],
  "skipped": [
    {
      "id": "L1-S001",
      "pattern": "/tmp/ usage",
      "reason": "Standard temp directory, universally available",
      "location": {"file": "hooks/lib/cache.py", "line": 12}
    }
  ],
  "patterns": [
    {
      "pattern": "All hardcoded paths use /home/user/cc as base",
      "occurrences": 15,
      "fix_leverage": "Single PROJECT_ROOT change would fix all"
    }
  ]
}
```

## Field Definitions

### Severity Levels

| Level | Meaning | User Experience |
|-------|---------|-----------------|
| **blocker** | Code fails immediately | `FileNotFoundError`, `KeyError` |
| **warning** | Feature may break | Partial functionality |
| **note** | Suboptimal but works | Minor inconvenience |

### Portability Score

| Score | Grade | Meaning |
|-------|-------|---------|
| 4.5-5.0 | A | Portable out of box |
| 3.5-4.4 | B | Minor adjustments needed |
| 2.5-3.4 | C | Significant setup required |
| 1.5-2.4 | D | Major rework needed |
| 0-1.4 | F | Not portable |

### Effort Estimates

| Effort | Meaning | Typical Fix |
|--------|---------|-------------|
| **trivial** | One-line change | Add `os.environ.get()` |
| **low** | Simple refactor | Add fallback chain |
| **medium** | Design change | Add config layer |
| **high** | Architecture change | Abstract all paths |

### Location Object

```json
{
  "file": "relative/path/from/root.py",
  "line": 45,
  "symbol": "function_name",
  "context": "Optional surrounding context"
}
```

### Fix Object

```json
{
  "pattern": "Brief description of fix approach",
  "code_before": "Original problematic code",
  "code_after": "Fixed portable code",
  "notes": "Any caveats or considerations"
}
```

## Categories by Lens

| Lens | Categories |
|------|------------|
| 1. Paths | `user_path`, `absolute_path`, `claude_specific`, `cwd_assumption` |
| 2. Env Vars | `undocumented_required`, `no_default`, `import_time_check` |
| 3. Tools | `mcp_dependency`, `claude_code_only`, `shell_specific`, `tool_assumption` |
| 4. Infrastructure | `tmux_version`, `sqlite_config`, `git_hooks`, `worktree_specific` |
| 5. Services | `required_api`, `network_required`, `no_mock`, `undocumented_service` |
| 6. Filesystem | `directory_assumption`, `permission_required`, `symlink_assumption` |
| 7. Config | `required_config`, `no_fallback`, `undocumented_options`, `no_example` |
| 8. Docs | `missing_section`, `undocumented_env`, `outdated_docs`, `implicit_knowledge` |

## Writing Guidelines

1. **Evidence required** - Quote actual code, not descriptions
2. **Impact on users** - How would a new user experience this?
3. **Actionable fixes** - Concrete code changes, not vague suggestions
4. **Effort calibration** - Be honest about complexity
5. **Pattern detection** - Group related issues for cascade fixes

## Validation Checklist

Before writing output, verify:
- [ ] All blockers have file:line locations
- [ ] Evidence includes actual code quotes
- [ ] Fix suggestions are syntactically valid
- [ ] Severity matches impact
- [ ] JSON is valid (parseable)
- [ ] Maximum 3 blockers, 5 warnings, 5 skipped
