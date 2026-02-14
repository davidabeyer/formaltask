# Synthesis Prompt

Exact prompt for Phase 4 - final report and actionable fix plan.

---

## THE EXACT PROMPT

```
PHASE 4: SYNTHESIS & FIX PLAN

INPUTS:
- {working_dir}/01-comprehension.md
- {working_dir}/02-*.json (all lens outputs)
- {working_dir}/03-hotspots.md

TARGET: {target_name}
OUTPUT: {working_dir}/04-final-report.md

YOUR MISSION: Transform findings into actionable cleanup plan.

═══════════════════════════════════════════════════════════════════════════
SYNTHESIS TASKS
═══════════════════════════════════════════════════════════════════════════

1. EXECUTIVE SUMMARY
   - Overall style health assessment
   - Critical issues requiring immediate attention
   - Recommended cleanup strategy

2. FINDINGS BY SEVERITY
   - All P0s with full details
   - All P1s grouped by type
   - P2/P3 summarized (details in appendix)

3. FINDINGS BY LENS
   - Top issues per lens
   - Cross-cutting patterns

4. AUTOMATED FIX OPPORTUNITIES
   - Issues fixable by tools (ruff, black, isort, autoflake)
   - Issues requiring manual review
   - Estimate: X% automatable

5. FIX COMMANDS
   - Linter/formatter commands
   - Specific sed/refactoring patterns
   - FormalTask commands for manual work

═══════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════

Write to: {working_dir}/04-final-report.md

```markdown
# Idiomatic Style Audit: {target_name}

**Generated:** {timestamp}
**Scope:** {target_path}

## Executive Summary

{2-3 paragraphs: overall assessment, critical findings, recommended approach}

**Style Health Score:** X/100
- Naming: X/100
- Typing: X/100
- Pythonic: X/100
- Organization: X/100
- Documentation: X/100
- Modernization: X/100

**Bottom Line:** {One sentence verdict}

---

## Critical Issues (P0)

{Full details for every P0 - these need immediate attention}

### P0-1: {Title}
**File:** `{file}:{line}`
**Lens:** {lens}

**Code:**
```python
{problematic code}
```

**Problem:** {Why this is P0}

**Fix:**
```python
{corrected code}
```

---

### P0-2: ...

---

## High Priority Issues (P1)

| # | Lens | Issue | File | Line |
|---|------|-------|------|------|
| 1 | typing | Missing return type on public API | api.py | 42 |
| 2 | ... | ... | ... | ... |

**Total P1 issues:** N

<details>
<summary>Full P1 Details</summary>

### P1-1: ...

</details>

---

## Medium Priority Issues (P2)

| Lens | Count | Common Pattern |
|------|-------|----------------|
| naming | X | Single-letter variables |
| typing | X | Missing parameter types |
| ... | ... | ... |

**Total P2 issues:** N

---

## Low Priority Issues (P3)

| Lens | Count | Example |
|------|-------|---------|
| modernization | X | dict() instead of {} |
| ... | ... | ... |

**Total P3 issues:** N

---

## Automated Fix Opportunities

### Fully Automatable ({X}% of issues)

```bash
# Fix import order
ruff check --select I --fix {target_path}

# Remove unused imports
ruff check --select F401 --fix {target_path}

# Fix formatting
ruff format {target_path}

# Type hint upgrades (Python 3.9+)
ruff check --select UP006,UP007 --fix {target_path}
```

### Semi-Automatable (require review)

```bash
# Find range(len()) patterns
ruff check --select C416 {target_path}

# Find == None comparisons
ruff check --select E711 {target_path}
```

### Manual Only

- Docstring additions
- Meaningful name improvements
- Architectural refactoring

---

## Hotspot Summary

| File | Score | Top Issue |
|------|-------|-----------|
| {file1} | 47 | Missing types |
| {file2} | 35 | Naming issues |
| ... | ... | ... |

See `03-hotspots.md` for full details.

---

## Recommended Fix Sequence

### Phase 1: Automated Cleanup (1 command)
```bash
ruff check --fix {target_path} && ruff format {target_path}
```
Expected impact: Fix ~{X}% of P2/P3 issues

### Phase 2: P0 Critical Fixes
{Numbered list of specific fixes}

### Phase 3: P1 High Priority
{Grouped by type for batch fixing}

### Phase 4: Hotspot Cleanup
{Address top 3-5 hotspots systematically}

---

## FormalTask Commands

```bash
# Critical fixes
python3 -m hooks.cli.pm task-add {epic} "Fix P0: {issue_title}"

# Batch style fixes
python3 -m hooks.cli.pm task-add {epic} "Style: Add missing return types to public API"
python3 -m hooks.cli.pm task-add {epic} "Style: Clean up {hotspot_file}"

# Documentation sprint
python3 -m hooks.cli.pm task-add {epic} "Docs: Add docstrings to {module}"
```

---

## Appendix: Full Findings

<details>
<summary>All Findings by File</summary>

### {file1.py}
- Line X: {issue}
- Line Y: {issue}

### {file2.py}
...

</details>

<details>
<summary>All Findings by Lens</summary>

### Naming
{Full list}

### Typing
{Full list}

...

</details>

---

## Verification Checklist

After fixes:
- [ ] `ruff check {target_path}` passes
- [ ] `mypy {target_path}` passes (if typed)
- [ ] Tests still pass
- [ ] No new style regressions
- [ ] Hotspot scores reduced

## Re-Audit Recommendation

After Phase 1-2 fixes, re-run: `idiomatic style audit {target_path}`
Expected: 50%+ reduction in findings
```

═══════════════════════════════════════════════════════════════════════════
AFTER WRITING
═══════════════════════════════════════════════════════════════════════════

Save to permanent location:

```python
from formaltask.utils.skill_output import write_skill_report

write_skill_report(
    skill="idiomatic-style-audit",
    title=f"Style Audit: {target_name}",
    content=report
)
```

═══════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════

1. COMPLETE INVENTORY - all findings must appear somewhere
2. PRIORITIZE CLEARLY - P0 first, always
3. ACTIONABLE OUTPUT - commands, not just descriptions
4. REALISTIC ESTIMATES - automated vs manual effort
5. ACKNOWLEDGE GOOD - don't make codebase sound terrible
```
