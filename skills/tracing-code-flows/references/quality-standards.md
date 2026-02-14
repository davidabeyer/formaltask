# Quality Standards

Standards for exhaustive, objective implementation evaluation.

## Exhaustiveness Criteria

The evaluation is not complete until:

- [ ] Every entry point has been identified
- [ ] Every happy path has been traced
- [ ] Every error path has been traced
- [ ] Edge cases enumerated for all inputs
- [ ] Adversarial scenarios considered for all inputs
- [ ] All seven gap categories evaluated
- [ ] At least one diagram per major component
- [ ] All findings have file:line references
- [ ] Risk levels assigned to all gaps

## Objectivity Requirements

- Report facts, not opinions
- Distinguish between "confirmed issue" and "potential concern"
- Provide evidence (code references) for all claims
- Acknowledge uncertainty when present
- Avoid solution prescriptions in gap descriptions (save for recommendations)

## Anti-Patterns to Avoid

| Anti-Pattern | Description |
|--------------|-------------|
| Superficial scanning | Do not skim; trace every path mentally |
| Assumption of correctness | Do not assume code works as intended |
| Missing the obvious | Check for common issues even if code looks clean |
| Tunnel vision | Evaluate all dimensions, not just the interesting ones |
| Incomplete enumeration | List ALL paths before analyzing ANY |
| Skipping adversarial | Always consider malicious inputs |
| Diagram-free reports | Every report needs visual flow documentation |

## Risk Severity Levels

**CRITICAL (P0)**
- Security vulnerability exploitable without authentication
- Data corruption or loss
- System crash/unavailability
- Compliance violation

**HIGH (P1)**
- Security vulnerability requiring authentication
- Data integrity issues
- Significant functionality broken
- Performance degradation >10x

**MEDIUM (P2)**
- Edge case failures
- Minor data issues
- Functionality degraded but works
- Performance degradation 2-10x

**LOW (P3)**
- Code quality issues
- Missing nice-to-have features
- Minor UX problems
- Documentation gaps
