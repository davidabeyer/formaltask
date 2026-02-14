# Common Documentation Review Scenarios

## Scenario 1: New Library README

**Trigger**: "Review this README for my new Python library"

**Process**:
1. Identify type: README Documentation
2. Load references/doc-best-practices.md
3. Check essential README sections:
   - Project description and purpose
   - Installation (pip install)
   - Quick start example
   - Link to full documentation
   - License, contributing guidelines
4. Score using rubric
5. Generate report with focus on "time to first success"

**Key Questions**:
- Can a developer understand what this does in 30 seconds?
- Can they install and run something in 5 minutes?
- Do they know where to go for more detail?

---

## Scenario 2: REST API Documentation

**Trigger**: "Check if this API documentation is complete"

**Process**:
1. Identify type: API Documentation
2. Load references/doc-best-practices.md
3. For each endpoint, verify:
   - HTTP method and URL
   - Authentication requirements
   - Request parameters (type, required/optional, defaults)
   - Response schema with examples
   - Error codes and meanings
   - Rate limits
4. Check for missing endpoints
5. Generate report highlighting incomplete endpoints

**Key Questions**:
- Is every public endpoint documented?
- Are error responses as detailed as success responses?
- Can a developer integrate without guessing?

---

## Scenario 3: Getting Started Guide

**Trigger**: "Does this tutorial make sense for beginners?"

**Process**:
1. Identify type: Tutorial/Guide Documentation
2. Load references/doc-best-practices.md
3. Evaluate:
   - Prerequisites stated upfront
   - Step-by-step instructions numbered
   - Expected output shown after each step
   - Code examples are copy-paste ready
   - Troubleshooting for common issues
   - Time estimate provided
4. Test mentally: Can a beginner follow this?
5. Generate report with focus on clarity and completeness

**Key Questions**:
- Are prerequisites complete and linked?
- Does each step have clear success criteria?
- What could go wrong and is it addressed?

---

## Scenario 4: Pre-Publication Review

**Trigger**: "Ready to publish these docs - any issues?"

**Process**:
1. Apply full scoring rubric
2. Check for critical issues:
   - Broken links
   - Outdated version references
   - Security vulnerabilities mentioned
   - Deprecated API usage
3. Quick wins for polish:
   - Consistent code formatting
   - Spell check technical terms
   - Update "last modified" date
4. Generate go/no-go recommendation

**Go/No-Go Criteria**:
- Score >= 75: GO (with noted improvements)
- Score 60-74: CONDITIONAL (fix high-priority first)
- Score < 60: NO-GO (rework required)

---

## Scenario 5: CLI Documentation

**Trigger**: "Review my CLI tool documentation"

**Process**:
1. Identify type: CLI Documentation
2. Check for:
   - All commands listed with descriptions
   - Flags/options documented (short and long forms)
   - Exit codes explained
   - Configuration files documented
   - Shell completion instructions
   - Examples for common workflows
3. Verify `--help` output matches documentation
4. Generate report

**Key Questions**:
- Can a user discover all features from docs?
- Are examples realistic workflows?
- Is error handling documented?

---

## Scenario 6: Configuration Documentation

**Trigger**: "Are all our config options documented?"

**Process**:
1. Identify type: Configuration Documentation
2. Cross-reference with code to find all options
3. For each option verify:
   - Name and description
   - Type and valid values
   - Default value
   - Required vs optional
   - Environment variable alternative
4. Check for complete working examples
5. Generate report with completeness focus

**Key Questions**:
- Are all options discoverable from docs alone?
- Are defaults clear so users know when to override?
- Are there examples for common configurations?

---

## Integration with Research

When reviewing documentation for unfamiliar technologies:

1. **Search for similar documentation** to establish baseline quality
2. **Research industry standards** for this documentation type
3. **Compare to reference implementations** (e.g., Stripe API docs, React documentation)
4. **Verify technical accuracy** by cross-referencing official specs

Use web search to find:
- Official style guides for the technology
- Highly-rated documentation examples
- Common pain points mentioned in developer forums
- Recent changes or deprecations
