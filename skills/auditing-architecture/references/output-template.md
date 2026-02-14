# Output Template

Final report format for deep code audits.

## Report Structure

```markdown
# Deep Audit: {target_path}

**Date:** {YYYY-MM-DD}
**Scope:** {description of what was analyzed}
**Modules Analyzed:** {count}

---

## Executive Summary

{2-3 sentences: Overall assessment and key findings}

**Findings:**
- Critical: {count}
- Significant: {count}
- Minor: {count}
- Rejected: {count} (detailed in appendix)

---

## Understanding Summary

### Purpose
{What this code exists to do - 1-2 sentences}

### Architecture
{Brief description of how it's structured}

### Key Insights
{Non-obvious things learned during comprehension phase}

---

## Modules Analyzed

### {Module 1 Name}

**Path:** `{path}`
**Purpose:** {what it does}
**Comprehension:** {brief summary of how it works}

### {Module 2 Name}
{...}

---

## Verified Findings

### Finding 1: {Title}

**Severity:** {Critical|Significant|Minor}
**Location:** `{file}:{start_line}-{end_line}`
**Category:** {Simplicity|Clarity|Data|Necessity|Testing|Liveness}

#### The Code

```{language}
{Actual code being discussed - include 5+ lines of context}
```

#### The Problem

{Specific explanation of why this is problematic IN THIS CONTEXT.
Not "could be better" - concrete impact.}

#### The Evidence

{Why we're confident this is a real issue:}
- {Evidence point 1}
- {Evidence point 2}
- {Verification result summary}

#### The Fix

**Before:**
```{language}
{current code}
```

**After:**
```{language}
{improved code}
```

**Why This Is Better:**
{Specific explanation - not just "cleaner"}

---

### Finding 2: {Title}
{repeat structure}

---

## Recommendations

Priority order for addressing findings:

1. **{Finding title}** - {Why first: unblocks others / highest impact}
2. **{Finding title}** - {Dependency or priority reason}
3. {etc.}

### Quick Wins
{Findings that can be fixed in <30 min with high confidence}

### Larger Efforts
{Findings that require more careful implementation}

---

## Appendix A: Rejected Findings

Findings that didn't survive verification. Included for transparency.

### Rejected: {Title}

**Initial Concern:** {What we thought was wrong}
**Verdict:** REJECTED
**Reason:** {Why it's not actually a problem}
**Evidence:** {What we found during verification}

---

## Appendix B: Out of Scope

Issues noticed but not analyzed (outside selected modules):

- `{file}:{line}` - {brief description}
- {etc.}

---

## Appendix C: Methodology

This audit followed the `auditing-code-deeply` protocol:

1. **Architecture Mapping** - Built comprehension before criticism
2. **Module Selection** - Focused on {criteria used}
3. **Deep Analysis** - Read all code, traced execution paths
4. **Adversarial Verification** - Actively attempted to disprove each finding
5. **Synthesis** - Compiled only verified findings

**Tools Used:**
- Semantic search: mcp__auggie-mcp__codebase-retrieval
- Pattern search: mcp__morph-mcp__warpgrep_codebase_search
- Git history: git blame, git log
- Full file reading: Read tool
```

---

## Quality Checklist

Before finalizing report:

- [ ] Every finding has actual code quoted (not just line references)
- [ ] Every finding has "The Problem" specific to this context
- [ ] Every finding has "The Evidence" explaining verification
- [ ] Every finding has concrete before/after code
- [ ] No findings use vague language ("could be better", "might cause issues")
- [ ] Rejected findings documented in appendix
- [ ] Severity accurately reflects impact
- [ ] Recommendations are prioritized with reasoning

---

## Saving the Report

```python
from formaltask.utils.skill_output import write_skill_report

report_content = """
{completed report markdown}
"""

write_skill_report(
    skill="auditing-code-deeply",
    title=f"Deep Audit: {target_name}",
    content=report_content
)
```

Reports saved to: `~/projects/deep-code-audit/reports/{date}-{slug}.md`
