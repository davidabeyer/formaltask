# Handoff: Gap Analysis - Configuration

**Parent Skill:** implementation-evaluator
**Gap Category:** Configuration
**Category Number:** 4 of 5
**Execution Mode:** PARALLEL (can run concurrently with categories 1-3, 5)
**Subagent Type:** general-purpose

---

## Verification

**STOP AND VERIFY BEFORE PROCEEDING:**

You are the **Configuration Gap Analyzer**.

- If this role does NOT match your spawn description, STOP and report mismatch.
- If the output location already exists with content, STOP and report conflict.

---

## Mission

You analyze the target implementation for **configuration gaps**. Focus on hardcoded values, missing environment variable handling, missing configuration validation, undocumented configuration options, and configuration security issues.

**Success Looks Like:** A comprehensive list of configuration gaps with severity, evidence, and recommendations for proper configuration management.

---

## Gap-Specific Checklist

Apply these specific checks for Configuration gaps:

### Hardcoded Values
- [ ] Are URLs hardcoded instead of configurable?
- [ ] Are ports/hosts hardcoded?
- [ ] Are timeout values hardcoded?
- [ ] Are file paths hardcoded?
- [ ] Are API endpoints hardcoded?
- [ ] Are feature flags hardcoded?

### Environment Variables
- [ ] Are required env vars documented?
- [ ] Are env vars validated at startup?
- [ ] Are missing env vars handled gracefully?
- [ ] Are env var names consistent (prefix pattern)?
- [ ] Are default values appropriate?

### Configuration Validation
- [ ] Are config values validated before use?
- [ ] Are type conversions safe (string to int, etc.)?
- [ ] Are value ranges checked?
- [ ] Are config errors reported clearly?

### Configuration Files
- [ ] Are config file locations configurable?
- [ ] Is there a config file schema?
- [ ] Are config files versioned/documented?
- [ ] Are config files properly parsed (not ad-hoc)?

### Secrets Management
- [ ] Are secrets in env vars, not config files?
- [ ] Are secrets excluded from version control?
- [ ] Are default/example configs secret-free?
- [ ] Are secrets rotatable without code changes?

### Environment Handling
- [ ] Are dev/staging/prod environments distinguishable?
- [ ] Are environment-specific overrides possible?
- [ ] Is configuration isolated per environment?
- [ ] Can configuration be changed without rebuild?

---

## Context You Need

### Your Specific Scope

**IN SCOPE:**
- Hardcoded values identification
- Environment variable usage
- Configuration validation
- Configuration file handling
- Secrets management
- Environment-specific handling

**OUT OF SCOPE (handled by other gap categories):**
- Error handling (Gap 1)
- Logging (Gap 2)
- Testing (Gap 3)
- Migration (Gap 5)

---

## Inputs

The parent agent will provide:

| Input | Description |
|-------|-------------|
| `SCOPE_FILES` | List of files in the implementation |
| `CONFIG_FILES` | Identified config files |
| `OUTPUT_FILE` | Path where you must write your findings |

---

## Expected Output

### Output File

**YOU MUST WRITE TO:** The `OUTPUT_FILE` path provided in your spawn prompt.

### Required Format

```markdown
# Gap Analysis: Configuration

**Analyzed:** {timestamp}
**Scope:** {implementation files}
**Subagent:** Gap 4 - Configuration

## Summary

{2-3 sentence executive summary of configuration gaps}

## Configuration Map

| Config Item | Source | Validated | Default | Notes |
|-------------|--------|-----------|---------|-------|
| `{config_1}` | {env/file/hardcoded} | {yes/no} | {value} | {notes} |
| `{config_2}` | {env/file/hardcoded} | {yes/no} | {value} | {notes} |

## Gap Inventory

### Hardcoded Value Gaps

#### Gap H1: {Short Title}
- **Severity:** {P0-Critical | P1-High | P2-Medium | P3-Low}
- **Location:** `{file}:{line}`
- **Gap Description:** {What is hardcoded}
- **Evidence:** {Code quote showing hardcoded value}
- **Impact:** {What deployment scenario is affected}
- **Recommendation:** {How to make configurable}

### Environment Variable Gaps

#### Gap E1: {Short Title}
...

### Validation Gaps

#### Gap V1: {Short Title}
...

### Config File Gaps

#### Gap F1: {Short Title}
...

### Secrets Gaps

#### Gap S1: {Short Title}
...

### Environment Handling Gaps

#### Gap N1: {Short Title}
...

## Coverage Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Hardcoded values | {NONE FOUND | SOME | MANY} | {details} |
| Env var handling | {COVERED | PARTIAL | MISSING} | {details} |
| Validation | {COVERED | PARTIAL | MISSING} | {details} |
| Config files | {COVERED | PARTIAL | MISSING} | {details} |
| Secrets handling | {SECURE | PARTIAL | INSECURE} | {details} |
| Environment handling | {COVERED | PARTIAL | MISSING} | {details} |

## Quality Checklist

- [ ] All 6 configuration aspects analyzed
- [ ] Each gap has severity, evidence, and recommendation
- [ ] No out-of-scope items analyzed
- [ ] File:line references for all gaps
- [ ] Output written to correct location
```

---

## Severity Guidelines for Configuration

| Severity | Criteria |
|----------|----------|
| **P0-Critical** | Secrets exposed or hardcoded |
| **P1-High** | Environment-specific values hardcoded |
| **P2-Medium** | Missing validation for config values |
| **P3-Low** | Inconsistent config patterns |

---

## Search Patterns

```python
# Find hardcoded URLs
Grep(pattern="https?://[^\"'\\s]+")

# Find hardcoded ports
Grep(pattern=":\\s*\\d{4,5}")

# Find environment variable access
Grep(pattern="(os\\.environ|process\\.env|getenv)")

# Find config file loading
Grep(pattern="(config|settings|\.env|\.yaml|\.json)")

# Find potential secrets
Grep(pattern="(password|secret|api_key|token)\\s*=\\s*[\"']")

# Find localhost references
Grep(pattern="localhost|127\\.0\\.0\\.1")
```

---

## Anti-Patterns to Avoid

- **False positives**: Constants like version numbers are OK hardcoded
- **Missing context**: Some hardcoded values are intentional (defaults)
- **Ignoring examples**: Check example/sample config files too
- **Scope creep**: Don't analyze test configuration (Gap 3)

---

**End of Configuration Gap Handoff**
