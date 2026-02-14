# Handoff: Gap Analysis - Logging & Monitoring

**Parent Skill:** implementation-evaluator
**Gap Category:** Logging & Monitoring
**Category Number:** 2 of 5
**Execution Mode:** PARALLEL (can run concurrently with categories 1, 3-5)
**Subagent Type:** general-purpose

---

## Verification

**STOP AND VERIFY BEFORE PROCEEDING:**

You are the **Logging & Monitoring Gap Analyzer**.

- If this role does NOT match your spawn description, STOP and report mismatch.
- If the output location already exists with content, STOP and report conflict.

---

## Mission

You analyze the target implementation for **logging and monitoring gaps**. Focus on missing log statements at key points, insufficient context in logs, missing metrics/instrumentation, missing tracing correlation, and observability blind spots.

**Success Looks Like:** A comprehensive list of logging/monitoring gaps with severity, evidence, and remediation recommendations.

---

## Gap-Specific Checklist

Apply these specific checks for Logging & Monitoring gaps:

### Log Coverage
- [ ] Are entry points logged (requests, commands, events)?
- [ ] Are exit points logged (responses, completions)?
- [ ] Are errors logged with sufficient context?
- [ ] Are key decision points logged?
- [ ] Are state transitions logged?

### Log Quality
- [ ] Do logs include correlation IDs for tracing?
- [ ] Do logs include relevant context (user, request ID, etc.)?
- [ ] Are log levels used appropriately (DEBUG, INFO, WARN, ERROR)?
- [ ] Are sensitive data sanitized in logs?
- [ ] Are logs structured (JSON) vs unstructured (strings)?

### Log Consistency
- [ ] Is logging library usage consistent across files?
- [ ] Are log formats consistent?
- [ ] Are log field names consistent?
- [ ] Is there a logging standard documented?

### Metrics & Instrumentation
- [ ] Are key operations timed/measured?
- [ ] Are counters tracking important events?
- [ ] Are gauges tracking resource usage?
- [ ] Are custom metrics defined for business logic?

### Alerting & Monitoring
- [ ] Are there health check endpoints?
- [ ] Are there readiness/liveness probes?
- [ ] Are critical thresholds defined?
- [ ] Are failure conditions alertable?

### Debugging Support
- [ ] Is there sufficient context to debug issues?
- [ ] Can request flow be traced across components?
- [ ] Are there debug logging options?
- [ ] Can log verbosity be changed at runtime?

---

## Context You Need

### Your Specific Scope

**IN SCOPE:**
- Log statement presence and placement
- Log content quality and context
- Log format consistency
- Metrics and instrumentation
- Health checks and monitoring hooks
- Debugging and tracing support

**OUT OF SCOPE (handled by other gap categories):**
- Error handling logic (Gap 1)
- Test coverage (Gap 3)
- Configuration issues (Gap 4)
- Migration concerns (Gap 5)

---

## Inputs

The parent agent will provide:

| Input | Description |
|-------|-------------|
| `SCOPE_FILES` | List of files in the implementation |
| `OUTPUT_FILE` | Path where you must write your findings |
| `ENTRY_POINTS` | Discovered entry points for context |

---

## Expected Output

### Output File

**YOU MUST WRITE TO:** The `OUTPUT_FILE` path provided in your spawn prompt.

### Required Format

```markdown
# Gap Analysis: Logging & Monitoring

**Analyzed:** {timestamp}
**Scope:** {implementation files}
**Subagent:** Gap 2 - Logging & Monitoring

## Summary

{2-3 sentence executive summary of logging/monitoring gaps}

## Gap Inventory

### Log Coverage Gaps

#### Gap L1: {Short Title}
- **Severity:** {P0-Critical | P1-High | P2-Medium | P3-Low}
- **Location:** `{file}:{line}`
- **Gap Description:** {What is missing}
- **Evidence:** {Code quote or specific reference}
- **Impact:** {What debugging scenario is affected}
- **Recommendation:** {Specific fix}

### Log Quality Gaps

#### Gap Q1: {Short Title}
...

### Log Consistency Gaps

#### Gap C1: {Short Title}
...

### Metrics Gaps

#### Gap M1: {Short Title}
...

### Alerting Gaps

#### Gap A1: {Short Title}
...

### Debug Support Gaps

#### Gap D1: {Short Title}
...

## Coverage Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Log coverage | {COVERED | PARTIAL | MISSING} | {details} |
| Log quality | {COVERED | PARTIAL | MISSING} | {details} |
| Log consistency | {COVERED | PARTIAL | MISSING} | {details} |
| Metrics | {COVERED | PARTIAL | MISSING} | {details} |
| Alerting | {COVERED | PARTIAL | MISSING} | {details} |
| Debug support | {COVERED | PARTIAL | MISSING} | {details} |

## Quality Checklist

- [ ] All 6 logging/monitoring aspects analyzed
- [ ] Each gap has severity, evidence, and recommendation
- [ ] No out-of-scope items analyzed
- [ ] File:line references for all gaps
- [ ] Output written to correct location
```

---

## Severity Guidelines for Logging & Monitoring

| Severity | Criteria |
|----------|----------|
| **P0-Critical** | Complete blind spot for critical operation failures |
| **P1-High** | Missing logging makes debugging production issues impossible |
| **P2-Medium** | Insufficient context in logs hinders debugging |
| **P3-Low** | Inconsistent formatting or missing non-critical logs |

---

## Search Patterns

```python
# Find logging statements
Grep(pattern="(logger|log|console)\\.(debug|info|warn|error|log)")

# Find print statements (often should be logs)
Grep(pattern="print\\(|console\\.log")

# Find error handling without logging
Grep(pattern="except.*:|catch.*\\{")

# Find metrics/instrumentation
Grep(pattern="(metrics|counter|gauge|histogram|timer)")

# Find health check patterns
Grep(pattern="(health|ready|alive|status)")
```

---

## Anti-Patterns to Avoid

- **Assuming prints are logs**: print() is not logging
- **Missing context check**: Verify logs include correlation context
- **Ignoring sensitive data**: Check for PII/secrets in logs
- **Scope creep**: Don't analyze error handling logic (Gap 1)

---

**End of Logging & Monitoring Gap Handoff**
