# Handoff Template: Gap Category Analysis

**Purpose**: Template for delegating gap category analysis to parallel subagents. Each subagent analyzes the entire implementation through one specific gap category lens.

**Usage**: Main agent fills placeholders `{...}` with implementation-specific context.

---

# Handoff: Gap Analysis - {gap_category_name}

**Parent Skill:** implementation-evaluator
**Gap Category:** {gap_category_name}
**Category Number:** {N} of 5
**Execution Mode:** PARALLEL (can run concurrently with other gap categories)
**Subagent Type:** general-purpose
**Output Location:** {output_path}

---

## Verification

**STOP AND VERIFY BEFORE PROCEEDING:**

You are the **{gap_category_name} Gap Analyzer**.

- If this role does NOT match your spawn description, STOP and report mismatch.
- If the output location already exists with content, STOP and report conflict.

---

## Mission

You analyze the target implementation for gaps specifically related to **{gap_category_name}**. You scan all files in scope, identify missing or inadequate handling, and provide actionable findings.

**Success Looks Like:** A comprehensive list of {gap_category_name} gaps with severity, evidence, impact, and recommendations.

---

## Context You Need

### Implementation Scope

{List of files/directories in scope for this implementation}

### Your Specific Scope

**IN SCOPE:**
{List of specific aspects this gap category should analyze}

**OUT OF SCOPE (handled by other gap categories):**
{List of aspects handled by other gap analyzers}

### Entry Points Discovered

{List of entry points from Phase 1 - for context only}

---

## Inputs Provided

### Files to Analyze

| Category | Path(s) | Focus Area |
|----------|---------|------------|
| Main Implementation | `{main_files}` | Core logic |
| Configuration | `{config_files}` | Settings |
| Tests | `{test_files}` | Coverage |

### Component Inventory

{Component table from Phase 1 discovery}

---

## Expected Output

### Output File

**YOU MUST WRITE TO:** `{output_path}`

### Required Format

```markdown
# Gap Analysis: {gap_category_name}

**Analyzed:** {timestamp}
**Scope:** {implementation_scope}
**Subagent:** Gap Category - {gap_category_name}

## Summary

{2-3 sentence executive summary of gap findings}

## Gap Inventory

### Critical Gaps (P0)

#### Gap C1: {Short Title}
- **Severity:** P0-Critical
- **Location:** `{file}:{line}`
- **Gap Description:** {What is missing}
- **Evidence:** {Quote or specific reference}
- **Impact:** {What breaks if not addressed}
- **Recommendation:** {Actionable fix}

### High-Priority Gaps (P1)

#### Gap H1: {Short Title}
- **Severity:** P1-High
- **Location:** `{file}:{line}`
- **Gap Description:** {What is missing}
- **Evidence:** {Quote or specific reference}
- **Impact:** {What breaks if not addressed}
- **Recommendation:** {Actionable fix}

### Medium-Priority Gaps (P2)

#### Gap M1: {Short Title}
...

### Low-Priority Gaps (P3)

#### Gap L1: {Short Title}
...

## Coverage Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| {aspect_1} | {COVERED | PARTIAL | MISSING} | {details} |
| {aspect_2} | {COVERED | PARTIAL | MISSING} | {details} |

## Quality Checklist

- [ ] All {gap_category_name} aspects analyzed
- [ ] Each gap has severity, evidence, and recommendation
- [ ] No out-of-scope items analyzed
- [ ] File:line references for all gaps
- [ ] Output written to correct location
```

---

## Severity Guidelines

| Severity | Criteria |
|----------|----------|
| **P0-Critical** | Gap WILL cause failures in production |
| **P1-High** | Gap LIKELY to cause issues under normal use |
| **P2-Medium** | Gap may cause issues in edge cases |
| **P3-Low** | Gap is a best practice violation with minimal impact |

---

## Tools You Should Use

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `Read` | Load files | Read implementation files |
| `Write` | Save output | Write gaps to output location |
| `Grep` | Search patterns | Find patterns related to gap category |
| `Glob` | Find files | Locate relevant files |

---

## Anti-Patterns to Avoid

- **Scope creep**: Stay within YOUR gap category only
- **Vague gaps**: "Error handling could be better" - be specific
- **Missing evidence**: Every gap needs a concrete code reference
- **No impact**: Explain WHY this gap matters
- **Generic recommendations**: Provide actionable, specific fixes

---

## Verification Steps

### Before Writing Output

1. [ ] All category-specific aspects analyzed
2. [ ] Each gap has all required fields
3. [ ] Severity levels justified
4. [ ] Stayed within scope

### After Writing Output

1. [ ] Output written to correct path
2. [ ] Output follows required format
3. [ ] Quality checklist completed

---

**End of Gap Category Handoff Template**
