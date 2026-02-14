---
consumes: [doc-drafts]
produces: [verified-docs]
---
# Phase 6: Verification (Adversarial Subagent)

Verify documentation matches code behavior.

## Subagent

```python
Task(
    subagent_type="general-purpose",
    description="Verify documentation accuracy",
    prompt=f"""
PHASE 6: DOCUMENTATION VERIFICATION

WORKING DIR: {run.run_dir}

Read the drafts:
- README: {run.run_dir}/05-readme-draft.md
- CLAUDE.md: {run.run_dir}/05-claudemd-draft.md

For EACH claim in the documentation:

1. FIND THE CODE
   - Locate the actual implementation
   - Quote the relevant lines

2. VERIFY THE CLAIM
   - Does the doc match the code?
   - Are edge cases accurate?
   - Do examples actually work?

3. CHECK CROSS-REFERENCES
   - Do links point to real files?
   - Are file paths correct?
   - Are line numbers current?

VERDICTS:
- ACCURATE: Claim matches code
- INACCURATE: Claim differs from code (explain)
- UNVERIFIABLE: Cannot find code to verify

WRITE TO: {run.run_dir}/06-verification.md

Flag any inaccuracies for correction before final output.
"""
)
```

See [verification-protocol.md](../references/verification-protocol.md) for full protocol.
