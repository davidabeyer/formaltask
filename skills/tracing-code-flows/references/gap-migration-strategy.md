# Handoff: Gap Analysis - Migration Strategy

**Parent Skill:** implementation-evaluator
**Gap Category:** Migration Strategy
**Category Number:** 5 of 5
**Execution Mode:** PARALLEL (can run concurrently with categories 1-4)
**Subagent Type:** general-purpose

---

## Verification

**STOP AND VERIFY BEFORE PROCEEDING:**

You are the **Migration Strategy Gap Analyzer**.

- If this role does NOT match your spawn description, STOP and report mismatch.
- If the output location already exists with content, STOP and report conflict.

---

## Mission

You analyze the target implementation for **migration strategy gaps**. Focus on backwards compatibility concerns, version migration paths, data migration handling, deprecation strategies, rollback capabilities, and upgrade documentation.

**Success Looks Like:** A comprehensive list of migration-related gaps with severity, evidence, and recommendations for safe deployment/upgrade paths.

---

## Gap-Specific Checklist

Apply these specific checks for Migration Strategy gaps:

### Backwards Compatibility
- [ ] Will existing clients/users break with new changes?
- [ ] Are API contracts preserved?
- [ ] Are data formats compatible with older versions?
- [ ] Are configuration file formats backwards compatible?
- [ ] Are database schemas backwards compatible?

### Version Migration
- [ ] Is there a clear versioning strategy?
- [ ] Are version numbers meaningful (semantic versioning)?
- [ ] Is there version detection in the code?
- [ ] Can different versions coexist during migration?
- [ ] Are version-specific code paths documented?

### Data Migration
- [ ] Are there database migration scripts?
- [ ] Are migrations reversible?
- [ ] Are migrations idempotent?
- [ ] Is there data validation after migration?
- [ ] Are large data migrations handled (batching)?

### Deprecation
- [ ] Are deprecated features marked clearly?
- [ ] Are deprecation warnings logged?
- [ ] Is there a deprecation timeline?
- [ ] Are replacement features documented?
- [ ] Are deprecated features still functional?

### Rollback Capability
- [ ] Can the deployment be rolled back?
- [ ] Are database migrations reversible?
- [ ] Is there a rollback procedure documented?
- [ ] Are rollback scenarios tested?
- [ ] Can partial rollbacks be performed?

### Upgrade Documentation
- [ ] Are upgrade steps documented?
- [ ] Are breaking changes documented?
- [ ] Are prerequisites documented?
- [ ] Is there a changelog/release notes?
- [ ] Are common upgrade issues documented?

---

## Context You Need

### Your Specific Scope

**IN SCOPE:**
- Backwards compatibility analysis
- Version handling patterns
- Data migration scripts/logic
- Deprecation handling
- Rollback mechanisms
- Upgrade documentation

**OUT OF SCOPE (handled by other gap categories):**
- Error handling (Gap 1)
- Logging (Gap 2)
- Testing (Gap 3)
- Configuration (Gap 4)

---

## Inputs

The parent agent will provide:

| Input | Description |
|-------|-------------|
| `SCOPE_FILES` | List of files in the implementation |
| `MIGRATION_FILES` | Identified migration files |
| `OUTPUT_FILE` | Path where you must write your findings |

---

## Expected Output

### Output File

**YOU MUST WRITE TO:** The `OUTPUT_FILE` path provided in your spawn prompt.

### Required Format

```markdown
# Gap Analysis: Migration Strategy

**Analyzed:** {timestamp}
**Scope:** {implementation files}
**Subagent:** Gap 5 - Migration Strategy

## Summary

{2-3 sentence executive summary of migration strategy gaps}

## Compatibility Assessment

| Aspect | Backward Compatible | Forward Compatible | Notes |
|--------|--------------------|--------------------|-------|
| API | {yes/partial/no} | {yes/partial/no} | {notes} |
| Data format | {yes/partial/no} | {yes/partial/no} | {notes} |
| Config | {yes/partial/no} | {yes/partial/no} | {notes} |
| Database | {yes/partial/no} | {yes/partial/no} | {notes} |

## Gap Inventory

### Backwards Compatibility Gaps

#### Gap B1: {Short Title}
- **Severity:** {P0-Critical | P1-High | P2-Medium | P3-Low}
- **Location:** `{file}:{line}`
- **Gap Description:** {What breaks compatibility}
- **Evidence:** {Code or change that causes break}
- **Impact:** {What clients/users are affected}
- **Recommendation:** {How to maintain compatibility}

### Version Migration Gaps

#### Gap V1: {Short Title}
...

### Data Migration Gaps

#### Gap D1: {Short Title}
...

### Deprecation Gaps

#### Gap P1: {Short Title}
...

### Rollback Gaps

#### Gap R1: {Short Title}
...

### Documentation Gaps

#### Gap O1: {Short Title}
...

## Migration Path Assessment

### Current State
{Description of current version/state}

### Target State
{Description of target version/state}

### Migration Steps
1. {Step 1}
2. {Step 2}
3. {Step N}

### Risk Points
- {Risk 1 with mitigation}
- {Risk 2 with mitigation}

## Coverage Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Backwards compatibility | {MAINTAINED | PARTIAL | BROKEN} | {details} |
| Version handling | {COVERED | PARTIAL | MISSING} | {details} |
| Data migration | {COVERED | PARTIAL | MISSING} | {details} |
| Deprecation | {COVERED | PARTIAL | MISSING} | {details} |
| Rollback | {COVERED | PARTIAL | MISSING} | {details} |
| Documentation | {COVERED | PARTIAL | MISSING} | {details} |

## Quality Checklist

- [ ] All 6 migration aspects analyzed
- [ ] Each gap has severity, evidence, and recommendation
- [ ] No out-of-scope items analyzed
- [ ] File:line references for all gaps
- [ ] Output written to correct location
```

---

## Severity Guidelines for Migration Strategy

| Severity | Criteria |
|----------|----------|
| **P0-Critical** | Breaking change with no migration path |
| **P1-High** | Data loss possible during migration |
| **P2-Medium** | Missing rollback capability |
| **P3-Low** | Documentation gaps or minor compatibility issues |

---

## Search Patterns

```python
# Find version handling
Grep(pattern="(version|VERSION|__version__|v\\d+\\.\\d+)")

# Find deprecation markers
Grep(pattern="(@deprecated|DEPRECATED|deprecation|deprecated)")

# Find migration files
Glob(pattern="**/migrations/**") or Glob(pattern="**/migrate*")

# Find schema changes
Grep(pattern="(ALTER|CREATE|DROP|ADD COLUMN|REMOVE)")

# Find breaking change indicators
Grep(pattern="(BREAKING|breaking change|incompatible)")

# Find changelog/release notes
Glob(pattern="**/CHANGELOG*") or Glob(pattern="**/RELEASE*")
```

---

## Anti-Patterns to Avoid

- **Assuming clean slate**: Existing deployments need migration
- **Ignoring rollback**: Every migration needs a reversal plan
- **Missing data concerns**: Schema changes affect production data
- **Scope creep**: Don't analyze test migrations (Gap 3)

---

**End of Migration Strategy Gap Handoff**
