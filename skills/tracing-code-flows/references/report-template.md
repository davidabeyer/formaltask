# Report Template

Standard structure for implementation evaluation reports.

## Report Location

```bash
mkdir -p ~/projects/implementation-evaluations
```

**Filename format:** `{descriptive-topic}-{YYYY-MM-DD}.md`

## Full Report Structure

```markdown
# Implementation Evaluation: {Implementation Name}

**Evaluator:** Claude (implementation-evaluator skill)
**Date:** {ISO date}
**Version:** v{N}
**Scope:** {directories/files evaluated}

---

## Executive Summary

{300-500 words maximum}

### Key Findings
- {Critical finding 1}
- {Critical finding 2}
- {Critical finding 3}

### Risk Assessment
| Risk Level | Count | Top Concerns |
|------------|-------|--------------|
| Critical   | N     | {brief}      |
| High       | N     | {brief}      |
| Medium     | N     | {brief}      |
| Low        | N     | {brief}      |

### Top 5 Recommendations
1. {Highest priority action}
2. {Second priority action}
3. ...

---

## Detailed Analysis

### 1. Architecture Overview

{Component inventory table}

{Architecture diagram - Mermaid}

### 2. Entry Points & Paths

{For each entry point:}
#### {Entry Point Name}

**Happy Paths:**
{Path walkthroughs}

**Error Paths:**
{Path walkthroughs}

**Edge Cases:**
{Path walkthroughs}

**Adversarial Scenarios:**
{Path walkthroughs}

{Control flow diagram - Mermaid}

### 3. Gap Inventory

#### Critical Gaps
{Detailed findings with code references}

#### High-Priority Gaps
{Detailed findings with code references}

#### Medium-Priority Gaps
{Detailed findings with code references}

#### Low-Priority Gaps
{Detailed findings with code references}

### 4. State & Data Flow

{State transition diagram if applicable}

{Data flow diagram}

### 5. Dependency Analysis

{Dependency graph - Mermaid}

{Coupling analysis}

{Circular dependency findings}

---

## Appendices

### A. Complete Path Enumeration
{Full structured list of all paths}

### B. All Diagrams
{Collected Mermaid diagrams for easy reference}

### C. Code References
{File:line references for all findings}
```

## Concise Report Option

For smaller implementations, use abbreviated format:

```markdown
# Evaluation: {Name}

**Date:** {date} | **Scope:** {files}

## Summary
{2-3 sentences}

## Findings
| Priority | Issue | Location | Recommendation |
|----------|-------|----------|----------------|
| Critical | ... | file:line | ... |
| High | ... | file:line | ... |

## Key Diagram
{Single most important Mermaid diagram}

## Next Steps
1. ...
2. ...
```
