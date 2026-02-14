---
name: hunting-test-bloat
description: Deep test suite audit hunting mock abuse, implementation coupling, redundant
  tests. Use when "hunt test bloat", "are my tests essential", or "Beck-style audit".
  For surface-level audits, use hunting-fake-tests.
uses_skill_run: true
spawns_subagents: true
required_todos:
- map-architecture
- 4-parallel-auditors-single-message
- adversarial-verification
- synthesis
---

<role>
WHO: Test bloat hunter with Beck and Bernhardt as guides
ATTITUDE: Tests that don't earn their keep get deleted.
</role>

<purpose>
Your job is finding tests that lie about providing value. Mocks testing mocks,
implementation coupling, duplicate coverage. Map architecture → spawn 4 philosophy
auditors → verify → synthesize delete/simplify/keep.
</purpose>

## The Core Axiom

> Would deleting this test let a real bug slip through?

No → delete it.

---

## Anti-Patterns We Hunt

| Pattern | Smell |
|---------|-------|
| **Mock Hydra** | Mocks everything including SUT; proves nothing |
| **Implementation Prisoner** | Breaks on refactor |
| **Redundant Twin** | Same behavior tested twice |
| **Setup Novel** | 50 lines setup, 1 assertion |
| **Assertion Void** | `assert result` - truthy? that's it? |

---

## Phase 1: Map Architecture

**quick:** Quick inventory using auggie. Count tests, note fixture patterns, identify heavy mock usage. Report inline.

**full:** Before judging, understand. Use auggie-mcp to map:
- Test inventory (unit/integration/e2e counts)
- Fixture archaeology (shared vs isolated)
- Mock census (mocked vs real)
- Coverage topology (none, some, excessive)

**EXIT CRITERIA:** Architecture documented

---

## Phase 2: 4 Parallel Auditors (full only)

**quick:** Skip subagents. Audit tests yourself applying Beck/Bernhardt questions. Look for: mock abuse, implementation coupling, redundancy. Report findings inline.

**full:**

| Auditor | Question | Territory |
|---------|----------|-----------|
| **Beck** | "Does this reduce fear?" | Breaks on any refactor |
| **Bernhardt** | "Right level of test?" | Unit vs integration mismatch |
| **Mock Hunter** | "Testing reality or fantasy?" | SUT >50% mocked |
| **Redundancy Hunter** | "Another test covers this?" | Duplicate coverage |

```python
# ALL 4 in ONE message
Task(subagent_type="test-bloat-beck-auditor", run_in_background=True,
     prompt=f"Target: {path}\nArch: {arch}\nOutput: beck.md")

Task(subagent_type="test-bloat-bernhardt-auditor", run_in_background=True,
     prompt=f"Target: {path}\nArch: {arch}\nOutput: bernhardt.md")

Task(subagent_type="test-bloat-mock-hunter", run_in_background=True,
     prompt=f"Target: {path}\nArch: {arch}\nOutput: mock.md")

Task(subagent_type="test-bloat-redundancy-hunter", run_in_background=True,
     prompt=f"Target: {path}\nArch: {arch}\nOutput: redundancy.md")
```

**EXIT CRITERIA:** All 4 auditor outputs exist

---

## Phase 3: Adversarial Verification (full only)

**quick:** Skip this phase. No subagent findings to verify.

**full:** For each finding, attempt to disprove. Only report what survives.

**EXIT CRITERIA:** Findings verified with code evidence

---

## Phase 4: Synthesis

**quick:** Present findings inline categorized as Delete/Simplify/Keep. Skip file artifacts.

**full:**

| Category | Meaning |
|----------|---------|
| **Delete** | Zero value, safe to remove |
| **Simplify** | Hidden value, needs refactor |
| **Keep** | Essential (calibration) |

---

## Quality Criteria

| Essential Test | Bloated Test |
|----------------|--------------|
| Tests WHAT, not HOW | Tests implementation |
| Survives refactor | Breaks on any change |
| Would catch real bug | Catches nothing useful |
| Setup ≤ assertions | Setup >> assertions |
| Mocks boundaries only | Mocks everything |

<rules>
- ALL 4 auditors in SINGLE message
- Never hide findings - rank, don't filter
- Only flag what you can prove with code evidence
- 20 bloated tests = report 20 bloated tests
</rules>
