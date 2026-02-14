# Portability Audit Report: Claude Code Tooling

**Target:** `/home/user/cc`
**Date:** 2026-01-19
**Overall Grade:** C+ (Score: 3.3/5.0)

---

## Executive Summary

This codebase is a sophisticated Claude Code tooling infrastructure with well-designed infrastructure coupling (tmux version detection, SQLite fallbacks, cross-platform file locking). However, it has significant portability blockers centered around **hardcoded path fallbacks to `~/claude-code`** and **missing configuration templates**.

### Key Finding
**The `~/claude-code` hardcoded fallback in `hooks/lib/path_config.py:206` is the single highest-impact portability issue.** Fixing this one file would cascade to resolve ~30% of all findings.

---

## Blockers by Lens

| Lens | Grade | Blockers | Warnings | Key Issue |
|------|-------|----------|----------|-----------|
| 1. Paths | C | 3 | 3 | `~/claude-code` hardcoded fallbacks |
| 2. Env Vars | B | 1 | 2 | `os.environ[]` in dayflow_linear_sync |
| 3. Tools | B | 1 | 4 | `/bin/ps` hardcoded path |
| 4. Infrastructure | B+ | 0 | 2 | Well-managed with fallbacks |
| 5. Services | B | 1 | 4 | Raw API key access |
| 6. Filesystem | B | 1 | 3 | Symlinks without Windows fallback |
| 7. Config | C | 1 | 4 | No config templates |
| 8. Docs | C+ | 2 | 5 | Incomplete env var documentation |

**Total:** 10 blockers, 27 warnings

---

## Critical Path Blockers

### 1. `hooks/lib/path_config.py:206` - get_project_root() hardcoded fallback

**Evidence:**
```python
return Path.home() / "claude-code"
```

**Impact:** All code calling `get_project_root()` without `PROJECT_ROOT` env var gets wrong path. Users who clone repo elsewhere experience silent path resolution failures.

**Fix:**
```python
# Auto-detect project root from this file's location
return Path(__file__).resolve().parent.parent.parent
```

---

### 2. `hooks/config.py:40` - workflow.config.json required without defaults

**Evidence:**
```python
config_path = Path.home() / ".claude" / "workflow.config.json"
if not config_path.exists():
    raise FileNotFoundError(
        f"Configuration file not found: {config_path}\n"
        "Please create ~/.claude/workflow.config.json with server and paths configuration"
    )
```

**Impact:** Any hook using `load_config()` crashes immediately on new machines with `FileNotFoundError`.

**Fix:** Add `DEFAULT_CONFIG` dict and optional config file loading (matching `workflow-worker/src/config.ts` pattern).

---

### 3. `dayflow_linear_sync/__init__.py:480` - Raw os.environ[] access

**Evidence:**
```python
api_key=os.environ["OPENROUTER_API_KEY"],
```

**Impact:** Crashes with cryptic `KeyError: 'OPENROUTER_API_KEY'` - unlike `hooks/lib/openrouter_client.py` which has helpful error messages.

**Fix:** Use `os.environ.get()` with `ValueError` and guidance message.

---

## Systemic Patterns

### Pattern 1: ~/claude-code Hardcoded Fallbacks (HIGH LEVERAGE)

**Affected Files:**
- `hooks/lib/path_config.py:206` - get_project_root()
- `hooks/lib/path_config.py:188` - get_hook_script_path()
- `hooks/session_start/auto_index_worker.py:38` - DEFAULT_CODEBASE_PATH
- `hooks/generate-skill-rules.py:20` - SKILL_DIRS
- `.githooks/post-commit:30` - DB_PATH fallback
- `.githooks/pre-push:13` - FORMALTASK_DB

**Cascade Fix:** Fixing `path_config.py`'s `get_project_root()` to auto-detect from `__file__` location would resolve 6+ related issues.

---

### Pattern 2: Missing Configuration Templates (MEDIUM LEVERAGE)

**Missing Templates:**
- `~/.claude/workflow.config.json` - Required but no example
- `~/.claude/settings.json` - Used 200+ times, only partial example in `ccpm/`
- `~/.claude.json` - API key storage, no template

**Fix:** Create `examples/` directory with:
- `workflow.config.example.json`
- `settings.example.json`
- `claude.example.json`

---

### Pattern 3: Inconsistent API Key Handling (MEDIUM LEVERAGE)

| Location | Pattern | Result |
|----------|---------|--------|
| `hooks/lib/openrouter_client.py` | `os.environ.get()` + fallback to `~/.claude.json` | Helpful error |
| `dayflow_linear_sync/__init__.py` | `os.environ[]` | Cryptic KeyError |
| `agents/gemini-relationship-suggester.py` | `os.environ.get()` + RuntimeError | Good message |

**Fix:** Standardize on the `hooks/lib/openrouter_client._load_api_key()` pattern.

---

## Quick Wins (Trivial Effort, Immediate Impact)

| ID | File | Line | Current | Fix |
|----|------|------|---------|-----|
| L3-B001 | `hooks/session-end/cleanup_orphans.py` | 22 | `['/bin/ps', ...]` | `['ps', ...]` |
| L2-B001 | `dayflow_linear_sync/__init__.py` | 480 | `os.environ["..."]` | `os.environ.get("...")` |
| L6-B001 | `hooks/session-start/create_session_metadata.py` | 48 | No mkdir | Add `debug_log.parent.mkdir(parents=True, exist_ok=True)` |
| L8-B001 | `agents/gemini-relationship-suggester.py` | - | Undocumented | Add `GEMINI_API_KEY` to env var table |

---

## Strengths (What's Working Well)

1. **Infrastructure version detection with fallbacks**
   - `scripts/bin/task-worker-spawn:49` - tmux version check with worktree path fallback
   - `hooks/lib/db_connection.py:56` - WAL mode skip for temp paths

2. **Consistent directory creation**
   - 50+ occurrences of `mkdir(parents=True, exist_ok=True)` before writes

3. **Cross-platform file locking**
   - `hooks/lib/session_utils.py:23` - Windows (msvcrt) and Unix (fcntl) support

4. **Subprocess calls use relative paths**
   - 80+ subprocess calls use `['git', ...]`, `['tmux', ...]` not `/usr/bin/git`

---

## Recommended Fix Order

### Week 1: Critical Path
1. Fix `hooks/lib/path_config.py:206` - Replace hardcoded fallback with auto-detection
2. Add `DEFAULT_CONFIG` to `hooks/config.py` - Match TypeScript loader behavior
3. Create `examples/workflow.config.example.json`

### Week 2: API Key Standardization
4. Fix `dayflow_linear_sync/__init__.py:480` - Use proper error handling
5. Document `GEMINI_API_KEY` in README.md and CLAUDE.md
6. Sync env var tables between README.md and CLAUDE.md

### Week 3: Polish
7. Fix `/bin/ps` hardcoded path in `cleanup_orphans.py`
8. Add symlink fallbacks for Windows compatibility
9. Create remaining config templates

---

## Verification Checklist

- [ ] L1-B001: `hooks/lib/path_config.py:206` contains `Path.home() / "claude-code"`
- [ ] L2-B001: `dayflow_linear_sync/__init__.py:480` contains `os.environ["OPENROUTER_API_KEY"]`
- [ ] L3-B001: `hooks/session-end/cleanup_orphans.py:22` contains `'/bin/ps'`
- [ ] L6-B001: `hooks/session-start/create_session_metadata.py:48` writes to `~/.claude/` without mkdir
- [ ] L7-B001: `hooks/config.py:40` raises `FileNotFoundError` if config missing
- [ ] L8-B001: `agents/gemini-relationship-suggester.py` uses `GEMINI_API_KEY` (undocumented in README)
- [ ] L8-B002: No `workflow.config.example.json` exists in repository

---

## Appendix: All Lens Outputs

Full JSON outputs available at:
- `/tmp/portability-audit-1768831492/lens-1-output.json`
- `/tmp/portability-audit-1768831492/lens-2-output.json`
- `/tmp/portability-audit-1768831492/lens-3-output.json`
- `/tmp/portability-audit-1768831492/lens-4-output.json`
- `/tmp/portability-audit-1768831492/lens-5-output.json`
- `/tmp/portability-audit-1768831492/lens-6-output.json`
- `/tmp/portability-audit-1768831492/lens-7-output.json`
- `/tmp/portability-audit-1768831492/lens-8-output.json`
- `/tmp/portability-audit-1768831492/cross-cutting-analysis.json`
