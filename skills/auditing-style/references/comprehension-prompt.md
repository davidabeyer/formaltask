# Comprehension Prompt

Exact prompt for Phase 1 - understanding the codebase before style critique.

---

## THE EXACT PROMPT

```
PHASE 1: DEEP COMPREHENSION

TARGET: {target_path}
OUTPUT: {working_dir}/01-comprehension.md

YOUR MISSION: Understand the codebase BEFORE any critique.
Style reviews without context flag intentional patterns as violations.

═══════════════════════════════════════════════════════════════════════════
COMPREHENSION TASKS
═══════════════════════════════════════════════════════════════════════════

Use these tools aggressively:
- mcp__auggie-mcp__codebase-retrieval for semantic understanding
- mcp__morph-mcp__warpgrep_codebase_search for pattern tracing
- Grep for specific patterns
- Read for full file inspection

1. PROJECT CONTEXT
   - What does this codebase do?
   - What's the tech stack? (Python version matters for idiom choices)
   - Any style guides referenced? (.flake8, pyproject.toml, .editorconfig)
   - Is there a CLAUDE.md or README with style preferences?

2. INTENTIONAL PATTERNS
   - Are there documented style deviations? Why?
   - Legacy code sections that shouldn't be modernized?
   - External API constraints forcing non-idiomatic patterns?
   - Performance-critical sections with intentional verbosity?

3. CODEBASE CONVENTIONS
   - What naming patterns are ALREADY established?
   - How is typing used? (strict, partial, none?)
   - Import organization pattern in use?
   - Docstring style? (Google, NumPy, Sphinx, none?)

4. STYLE CONFIGURATION
   - Check: pyproject.toml, setup.cfg, .flake8, .pylintrc, .mypy.ini
   - What rules are explicitly configured?
   - What's ignored and why?

═══════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════

Write to: {working_dir}/01-comprehension.md

```markdown
# Codebase Comprehension: {target_name}

## Project Overview
{2-3 sentences on what this does}

## Tech Stack
- Python version: X.Y
- Key dependencies: ...
- Framework: ... (if any)

## Established Style Conventions

### Naming
- Functions: {observed pattern}
- Classes: {observed pattern}
- Constants: {observed pattern}
- Notable deviations: {if any, with reasons}

### Typing
- Coverage: none / partial / strict
- Style: old (`List[X]`) / modern (`list[X]`) / mixed
- Notable: {observations}

### Imports
- Order: {observed pattern}
- Grouping: {observed pattern}
- `__all__` usage: yes / no / inconsistent

### Documentation
- Docstring style: Google / NumPy / Sphinx / none / mixed
- Coverage: high / medium / low
- README quality: ...

## Intentional Deviations
{List any documented or clearly intentional non-idiomatic patterns}

1. {Pattern}: {Reason documented/inferred}
2. ...

## Style Configuration Files

### pyproject.toml
{Relevant style sections or "not present"}

### Other configs
{.flake8, .pylintrc, etc. or "none found"}

## Hotspot Candidates
{Files that appear to have most style variance - for Phase 3}

## Context for Reviewers
{Any other info that will help lens reviewers avoid false positives}
```

═══════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════

1. NO CRITIQUE YET - comprehension only
2. DOCUMENT INTENTIONS - why patterns exist matters
3. FIND STYLE CONFIGS - they override general rules
4. BE THOROUGH - this handoff is all lens reviewers get
```
