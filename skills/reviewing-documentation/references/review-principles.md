# Documentation Review Principles

## Be Specific

Vague feedback is not actionable. Replace general suggestions with precise recommendations.

| Bad | Good |
|-----|------|
| "improve clarity" | "define 'webhook' on first use in Getting Started section" |
| "add examples" | "add working example for user authentication flow" |
| "fix structure" | "move Configuration before Advanced Usage" |
| "needs more detail" | "document all error codes for the /users endpoint" |
| "unclear" | "replace 'set up the environment' with step-by-step commands" |

## Be Constructive

Reviews should help, not just criticize.

**Structure feedback positively**:
1. Acknowledge what works well
2. Explain WHY something matters (impact on developers)
3. Provide concrete before/after examples
4. Prioritize fixes by impact

**Example**:
> The installation section is excellent - clear steps with expected output shown.
>
> The authentication section needs work: developers won't know which token type to use. Consider adding a table comparing OAuth vs API keys with use cases for each. This would reduce support tickets about "which auth should I use?"

## Be Practical

Not all issues are equal. Prioritize effectively.

**Distinguish levels**:
- **Must-fix**: Blocks developers (missing install, broken examples)
- **Should-fix**: Degrades experience (missing errors, unclear flow)
- **Nice-to-have**: Polish (diagrams, videos, more examples)

**Consider constraints**:
- Maintenance burden of suggestions
- Team capacity and priorities
- Documentation tooling limitations

**Identify quick wins**:
- High impact, low effort improvements
- Things that can be done in 30 minutes or less
- Build momentum for larger changes

## Be Evidence-Based

Support findings with specific references.

**Do**:
- Reference specific sections by heading
- Quote problematic text directly
- Compare to documented best practices
- Use scoring rubric consistently
- Count occurrences (e.g., "5 of 12 endpoints missing error docs")

**Don't**:
- Make vague claims without examples
- Apply personal preferences as standards
- Ignore scoring rubric
- Skip the low-scoring dimensions

## Common Anti-Patterns to Reference

When identifying issues, reference these documented anti-patterns:

| Anti-Pattern | Symptom | Fix |
|--------------|---------|-----|
| The Missing Middle | Quickstart jumps to advanced, no tutorials | Add bridging content |
| The Assumptive Docs | "Simply configure X" without explaining X | Define prerequisites, add links |
| The Orphaned Example | Code without context | Explain before showing, show output |
| The Stale Docs | Old screenshots, deprecated APIs | Version tags, CI checks |
| The Wall of Text | Giant paragraphs, no breaks | Lists, tables, code blocks |
| The Vague Warning | "Be careful with this" | Specify exact risks and alternatives |

## Output Quality Checklist

Before finalizing a review, verify:

- [ ] All four dimensions (Structure, Completeness, Quality, DX) scored
- [ ] Scores justified with specific evidence
- [ ] Every issue has: location, problem, impact, recommendation
- [ ] Issues prioritized by severity (High/Medium/Low)
- [ ] At least 3 quick wins identified
- [ ] Recommendations are actionable (not vague)
- [ ] Strengths acknowledged (not just criticism)
- [ ] Maturity level assessed with path forward

## Adapting to Audience

**For maintainers (internal review)**:
- More technical depth
- Reference specific code locations
- Suggest tooling improvements

**For contributors (external feedback)**:
- Focus on user-facing issues
- Emphasize developer experience
- Avoid internal process recommendations

**For stakeholders (summary)**:
- Lead with score and rating
- Highlight business impact
- Recommend go/no-go decision
