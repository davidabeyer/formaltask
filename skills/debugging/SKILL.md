---
name: debugging
description: Systematic debugging with graded exploration and agent escalation. MUST
  BE USED when encountering errors, test failures, or unexpected behavior.
required_todos:
- meta-analysis
- quick-investigation
- systematic-analysis
- deep-trace
- pre-commit-adversarial
- commit-checkpoint
---

<role>
WHO: Root cause hunter
ATTITUDE: Symptom fixes are failure. Root cause or nothing.
</role>

<purpose>
Your job is to find the SOURCE, not where it hurts. Quick look first. If that fails, escalate.
</purpose>

<workflow>
## Phase 0: Meta-Analysis (MANDATORY)

**BLOCKING GATE:** Error or unexpected behavior exists.

**quick:** State the error and 2 hypotheses in plain text. Skip XML.

**full:** Before touching code, understand the problem conceptually:

```xml
<meta_analysis>
  <symptom>[Exact error message and location]</symptom>
  <surface_interpretation>[What this error literally means]</surface_interpretation>
  <deeper_question>[What STATE is invalid? Not "what line failed" but "what assumption was violated"]</deeper_question>
  <misdirection_risk>[Ways I could waste time—staring at symptom location when bug is upstream]</misdirection_risk>
  <root_cause_hypotheses>[2-3 possible root causes BEFORE looking at code]</root_cause_hypotheses>
</meta_analysis>
```

**EXIT CRITERIA:** Hypotheses formed. Now investigate with direction.

---

## Phase 1: Quick Investigation

**BLOCKING GATE:** Meta-analysis complete with hypotheses.

1. Parse error message and context
2. Semantic first (auggie), then exact (Grep)
3. Check for obvious causes (typos, missing imports, wrong params)

**full:** Use sequential reasoning to test hypotheses:

```xml
<sequential>
  <thought id="T1">[Test first hypothesis - evidence for/against]</thought>
  <thought id="T2" builds="T1">[What T1 implies about second hypothesis]</thought>
  <revision revises="T1" reason="[if evidence contradicts]">[Updated understanding]</revision>
</sequential>
```

**If root cause found → fix it and stop.**

**EXIT CRITERIA:** Either fixed, or need deeper investigation.

## Phase 2: Systematic Analysis

**BLOCKING GATE:** Phase 1 didn't solve it.

**quick:** Trace caller vs callee yourself. Check both paths, report findings inline.

**full:** When uncertain which layer has the bug, use branching:

```xml
<branching>
  <fork point="Bug in caller or callee?"/>
  <path id="caller">[Trace upward—who passed bad data? What state was wrong?]</path>
  <path id="callee">[Trace inward—what assumption violated? What edge case?]</path>
  <converge when="[Evidence showing which path has the source]"/>
</branching>
```

**full:** Spawn debug-specialist agent:

```python
Task(
    subagent_type="debug-specialist",
    description="Investigate: [error summary]",
    prompt=f"""Error: {error_message}
Context: {what_was_happening}
Already checked: {phase_1_findings}
Hypotheses from meta-analysis: {hypotheses}

Find root cause. Report back with:
- Reproduction steps
- Root cause with file:line evidence
- Recommended fix"""
)
```

**If root cause found → write failing test, fix, verify.**

**EXIT CRITERIA:** Either fixed, or need cross-file tracing.

## Phase 3: Deep Trace (full only)

**BLOCKING GATE:** Phase 2 didn't solve it.

Spawn code-analyzer for cross-file flow tracing:

```python
Task(
    subagent_type="code-analyzer",
    description="Trace: [error] through call chain",
    prompt=f"""Error occurs at: {location}
Trace backward through call chain to find original trigger.

For each level:
- What function called this?
- What parameters were passed?
- Where did those values come from?

Find the SOURCE of the problem, not where it manifests."""
)
```

## Hypothesis Verification (when uncertain)

If you have a theory but aren't sure:

```python
Task(
    subagent_type="claim-verifier",
    description="Verify: [hypothesis]",
    prompt=f"""Hypothesis: {your_theory}
Verify with evidence. Find file:line proof that confirms or refutes."""
)
```

---

## Phase 4: Pre-Commit Adversarial Check (full only)

**BLOCKING GATE:** Fix implemented.

Before committing, assume the fix will fail:

```xml
<adversarial>
  <future_state>6 months later. This "fix" regressed or caused new bugs.</future_state>
  <failure>[What went wrong—the fix was too narrow, missed edge case, broke something else]</failure>
  <cause>[What we should have caught before committing]</cause>
  <prevent>[Additional test or change that blocks this failure]</prevent>
</adversarial>
```

---

## Phase 5: Commit Checkpoint

**quick:** State "Fixed [error] because [root cause]. Test: [test name or N/A]." Done.

**full:**

**BLOCKING GATE:** Adversarial check complete.

```xml
<checkpoint>
  <verify>Does fix address ROOT CAUSE from meta_analysis hypotheses? [YES/NO + evidence]</verify>
  <verify>Test covers the specific failure mode? [YES/NO]</verify>
  <conclusion>[Commit message explaining WHY this fixes it]</conclusion>
  <flips_if>[What symptom would indicate this fix is wrong]</flips_if>
</checkpoint>
```
</workflow>

<rules>
- Root cause before fixes - symptom fixes are failure
- Escalate without asking - speed matters
- 3 fix limit - after 3 failures, stop and question architecture
- Test first on real fixes - write failing test before implementing
- Never mask problems - no defaults or guards at symptom site
- Re-run original failure before commit - test fixtures lie

</rules>
