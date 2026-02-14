---
consumes: [pass-findings]
produces: [verified-findings]
optional: true
---
## Phase 6: Verification (full only)

**quick:** Skip formal verification. Trust your inline findings.

**full:** Challenge every finding. Assume wrong until proven.

For each finding:
1. Re-read actual code
2. Check if intentional (documented deviation?)
3. Check if exemplar projects do this
4. Would 3 senior devs flag this?

Verdicts: CONFIRMED / REJECTED / MODIFIED

```python
Skill("verifying-claims")  # spot-check "single letter var", "missing type hint", "non-idiomatic" claims
```

**Auditors hypothesize. Verification confirms.**

**EXIT CRITERIA:** Verified findings in `03-verified.md`
