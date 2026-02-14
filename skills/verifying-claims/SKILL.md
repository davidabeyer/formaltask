---
name: verifying-claims
description: 'Fact-check anything. With args: verify specific claims. Without args:
  scan recent outputs and verify everything verifiable. Activates on "verify", "fact-check",
  "check yourself", or when skeptical of any analysis.'
---

<role>
WHO: Hallucination hunter
ATTITUDE: One search proves nothing. Exhaust every angle.
</role>

<purpose>
Catch lies before they ship. Claude invents functions, cites fixed bugs, misses context.
</purpose>

## Claim Types → Tools

| Type | Example | Tool |
|------|---------|------|
| Existence | "Function X in Y" | Grep |
| Behavior | "X does Y" | Augment |
| Relationship | "X calls Y" | warpgrep |
| Absence | "No tests for X" | ALL THREE (highest risk) |
| Numeric | "N files have X" | Grep count + verify ALL |
| Change | "X was removed" | git log + Grep |

## Workflow

### 0. Meta-Analysis

**quick:** Note verification stakes in one sentence. Skip XML.

**full:** Before extracting claims, understand verification context:

```xml
<meta_analysis>
  <verification_request>[What they asked—"verify X", "check yourself", or scanning own output]</verification_request>
  <stakes>[What happens if a claim is wrong? Misleading advice? Wasted refactor? Security hole?]</stakes>
  <bias_check>[Am I motivated to confirm my own claims? Check for self-confirmation bias.]</bias_check>
</meta_analysis>
```

### 1. Extract Claims

**With args:** Use provided claims.
**No args:** Scan recent outputs for verifiable statements.

Claim categories:
- Existence, Behavior, Relationship → standard verification
- Absence → triple-verify or stay silent

### 2. Prioritize

| P0 | Absence claims |
| P1 | Claims driving action |
| P2 | Behavioral claims |
| P3 | Incidental |

### 3. Verify

For each: search → read actual code → verdict.

**quick:** Verify claims inline. Report verdicts directly.

**full:** Use sequential reasoning to track how verifications affect each other:

```xml
<sequential>
  <thought id="V1">[First claim verification—e.g., "Function X exists at file:42"]</thought>
  <thought id="V2" builds="V1">[How V1 affects next claim—"but behavior claim about X is wrong"]</thought>
  <revision revises="V1" reason="[if deeper search contradicts]">[Updated verdict]</revision>
</sequential>
```

**Tool count gate:**
- Existence claims: ≥2 tools
- Absence claims: ≥3 tools (or mark UNVERIFIED)

| Verdict | Meaning |
|---------|---------|
| VERIFIED | Matches reality |
| REFUTED | Wrong (show correction) |
| PARTIAL | Partly true |
| DESIGN | Intentional choice mistaken as bug |

### 4. Report

**quick:** Report verdicts with evidence. Skip checkpoint XML.

**full:** Before final report, verify verification was thorough:

```xml
<checkpoint>
  <verify>Every claim got minimum tool count (2 for existence, 3 for absence)? [YES/NO]</verify>
  <verify>Absence claims marked UNVERIFIED if not triple-checked? [YES/NO]</verify>
  <verify>Refuted claims have corrections with evidence? [YES/NO]</verify>
  <conclusion>
    VERIFIED: [N]
    REFUTED: [N]
    CONFIDENCE: [High if all gates passed, Low if shortcuts taken]
  </conclusion>
  <flips_if>[What would change verdicts—e.g., "if there's a second implementation I missed"]</flips_if>
</checkpoint>
```

```markdown
| Verdict | Count |
|---------|-------|
| VERIFIED | N |
| PARTIAL | N |
| REFUTED | N |

## Corrections
| Claim | Stated | Actual |
|-------|--------|--------|
```

<rules>
- One search proves nothing (minimum: 2 for existence, 3+ for absence)
- Absence needs 3+ tools or don't claim it
- Read actual code - search results lie by omission
- Contradictions = someone's lying - find who
</rules>
