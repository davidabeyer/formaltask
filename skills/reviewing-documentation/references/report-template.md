# Documentation Review Report Template

Use this structure for all documentation reviews.

## Report Format

```markdown
## Technical Documentation Review: [Doc Name]

**Documentation Type**: [API/Library/CLI/Tutorial/README/Configuration]

**Overall Score**: X/100 (Rating: Excellent/Good/Acceptable/Poor)

---

### Summary

[2-3 sentences summarizing overall quality and key findings]

---

### Scoring Breakdown

**Structure**: X/30
**Completeness**: X/30
**Quality**: X/30
**Developer Experience**: X/10

---

### Strengths

- [Specific positive aspect 1]
- [Specific positive aspect 2]
- [Specific positive aspect 3]

---

### Issues Found

#### High Priority (Fix Immediately)

**Issue 1: [Title]**
- **Location**: [Section/heading]
- **Problem**: [What's wrong - reference anti-pattern if applicable]
- **Impact**: [Effect on developers]
- **Recommendation**: [Specific fix]
- **Example**:
  ```
  [Show before/after if applicable]
  ```

#### Medium Priority (Fix Soon)

[Same structure as high priority]

#### Low Priority (Nice to Have)

[Same structure]

---

### Recommendations by Category

**Completeness**
- [ ] Add [specific missing section]
- [ ] Document [specific undocumented feature]

**Clarity**
- [ ] Simplify [specific complex section]
- [ ] Define [specific undefined term]

**Examples**
- [ ] Add runnable example for [specific use case]
- [ ] Show expected output for [specific example]

**Developer Experience**
- [ ] Reduce time to first success (currently: X minutes)
- [ ] Add troubleshooting for [common error]

---

### Quick Wins

[3-5 high-impact, low-effort improvements that can be made immediately]

1. [Specific actionable item]
2. [Specific actionable item]
3. [Specific actionable item]

---

### Maturity Assessment

**Current Level**: [1-5 using maturity model from doc-best-practices.md]

**Path to Next Level**:
- [Specific requirement 1]
- [Specific requirement 2]
- [Specific requirement 3]

---

### Best Practices Comparison

[Compare against similar high-quality documentation in the same category]

**Examples of excellent [type] documentation**:
- [Example 1]: [What they do well]
- [Example 2]: [What they do well]

**Apply these patterns**:
- [Specific pattern to adopt]
- [Specific pattern to adopt]
```

## Scoring Thresholds

| Score | Rating | Meaning |
|-------|--------|---------|
| 90-100 | Excellent | Ship it, minor polish only |
| 75-89 | Good | Ready with some improvements |
| 60-74 | Acceptable | Needs work before publication |
| < 60 | Poor | Significant rework required |

## Issue Prioritization

**High Priority (Fix Immediately)**
- Missing getting started guide
- No installation instructions
- Code examples don't run
- Breaking changes undocumented
- Security issues not called out

**Medium Priority (Fix Soon)**
- Incomplete API reference
- Missing error documentation
- No troubleshooting section
- Inconsistent terminology
- Outdated examples

**Low Priority (Nice to Have)**
- More real-world examples
- Better diagrams
- Video tutorials
- Interactive demos
