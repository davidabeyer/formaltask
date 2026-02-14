# Hotspot Prompt

Exact prompt for Phase 3 - identifying files with concentrated style debt.

---

## THE EXACT PROMPT

```
PHASE 3: HOTSPOT ANALYSIS

INPUTS:
- {working_dir}/01-comprehension.md
- {working_dir}/02-naming.json
- {working_dir}/02-typing.json
- {working_dir}/02-pythonic.json
- {working_dir}/02-organization.json
- {working_dir}/02-documentation.json
- {working_dir}/02-modernization.json

OUTPUT: {working_dir}/03-hotspots.md

YOUR MISSION: Identify files with concentrated style debt.

═══════════════════════════════════════════════════════════════════════════
ANALYSIS TASKS
═══════════════════════════════════════════════════════════════════════════

1. AGGREGATE BY FILE
   For each file mentioned in any lens output:
   - Count total findings
   - Count findings per severity
   - Calculate "debt score": P0*10 + P1*5 + P2*2 + P3*1

2. IDENTIFY HOTSPOTS
   Files with debt score > threshold or multiple P0/P1 issues
   These are candidates for focused cleanup

3. PATTERN ANALYSIS
   - Do hotspots share characteristics? (age, author, feature area)
   - Are hotspots concentrated in one package/module?
   - Legacy code vs recent additions?

4. ROOT CAUSE HYPOTHESES
   - Missing team style guide?
   - Rushed feature development?
   - Multiple contributors with different styles?
   - Gradual drift without review?

═══════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════

Write to: {working_dir}/03-hotspots.md

```markdown
# Style Debt Hotspots

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total findings | N |
| P0 (critical) | N |
| P1 (high) | N |
| P2 (medium) | N |
| P3 (low) | N |
| Files affected | N |
| Hotspot files | N |

## Top 10 Hotspots

| Rank | File | Debt Score | P0 | P1 | P2 | P3 | Primary Issues |
|------|------|------------|----|----|----|----|----------------|
| 1 | path/to/file.py | 47 | 2 | 5 | 8 | 3 | typing, naming |
| 2 | ... | ... | ... | ... | ... | ... | ... |

## Hotspot Details

### #1: path/to/file.py (Score: 47)

**Breakdown by lens:**
- Naming: 3 issues (1 P1, 2 P2)
- Typing: 8 issues (2 P0, 4 P1, 2 P2)
- Pythonic: 2 issues (1 P2, 1 P3)
- ...

**Key issues:**
1. {Most impactful issue}
2. {Second most impactful}
3. {Third}

**Recommendation:** {Prioritized cleanup approach}

---

### #2: ...

## Pattern Analysis

### Concentration
{Are hotspots clustered in specific areas?}

### Age Factor
{Are hotspots older code or recent additions?}

### Root Causes
1. {Hypothesis 1}
2. {Hypothesis 2}

## Recommended Cleanup Order

1. **Quick wins:** Files with many P3s (fast fixes, visible progress)
2. **High impact:** Files with P0/P1 concentration
3. **Systematic:** Address by lens across codebase

## Files NOT Needing Attention

{Files with 0-2 minor issues - acknowledge good areas}
```

═══════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════

1. AGGREGATE ACCURATELY - parse all JSON outputs
2. PRIORITIZE BY IMPACT - debt score captures urgency
3. LOOK FOR PATTERNS - individual issues vs systemic problems
4. ACKNOWLEDGE GOOD CODE - not everything needs fixing
```
