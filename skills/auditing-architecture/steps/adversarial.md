---
consumes: [module-findings]
produces: [verified-findings]
optional: true
---
# Phase 4: Adversarial Verification (full only)

**quick:** Skip this phase.

**full:** Before spawning verifier, check your own work:

```xml
<adversarial>
  <future_state>Report shipped. Team spent a week on my recommendations. Half were wrong.</future_state>
  <preference_masquerade>[Which "findings" are actually MY style preferences, not real problems?]</preference_masquerade>
  <context_ignorance>[Which findings ignore historical context or constraints I don't know about?]</context_ignorance>
  <fix_worse_than_problem>[Which recommended fixes would introduce more complexity than they remove?]</fix_worse_than_problem>
</adversarial>
```

Now spawn verifier to DISPROVE every finding:

```python
Task(
    subagent_type="adversarial-verifier",
    description="Verify findings",
    prompt=f"""## FINDINGS
Read all module analyses in {run_dir}/outputs/03-module-*.md

## OUTPUT
{run_dir}/outputs/04-verified-findings.md

## TASK
ADVERSARIAL VERIFICATION

For EACH finding, attempt to disprove:
1. Search for explanation (comments, git blame, docs)
2. Check if pattern is consistent elsewhere (codebase convention?)
3. Trace all callers - does "problem" cause issues in practice?
4. Evaluate fix - does it compile? maintain behavior? introduce new issues?

Verdicts: CONFIRMED | REJECTED | MODIFIED
Only CONFIRMED findings make the final report."""
)

# Final codebase verification
Skill("verifying-claims")  # spot-check "dead code", "unused abstraction" claims
```
