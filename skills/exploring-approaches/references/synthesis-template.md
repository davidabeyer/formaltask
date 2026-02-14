# Synthesis Template

After all explorers complete, synthesize their findings into a comparison.

---

## Comparison Table

```markdown
## Approach Comparison: {feature_name}

| Aspect | Simple | Balanced | Scalable |
|--------|--------|----------|----------|
| **Philosophy** | {from explorer-1} | {from explorer-3} | {from explorer-2} |
| **Files Changed** | N | N | N |
| **New Dependencies** | N | N | N |
| **Error Handling** | Basic | Standard | Comprehensive |
| **Test Coverage** | Unit only | Unit + key integration | Full suite |
| **Effort** | Low | Medium | High |
| **Tech Debt Risk** | Higher | Moderate | Lower |

### Simple Approach
**Pros:** {bullets from explorer-1}
**Cons:** {bullets from explorer-1}
**Best if:** Speed matters most, requirements may change

### Balanced Approach
**Pros:** {bullets from explorer-3}
**Cons:** {bullets from explorer-3}
**Best if:** Need confidence without over-engineering

### Scalable Approach
**Pros:** {bullets from explorer-2}
**Cons:** {bullets from explorer-2}
**Best if:** This is core infrastructure, high traffic expected

---

**My Recommendation:** {Approach} because {specific rationale based on context}

**Which approach would you like to proceed with?**
```

---

## Decision Factors

Help user decide by surfacing:

| Factor | Favors Simple | Favors Balanced | Favors Scalable |
|--------|---------------|-----------------|-----------------|
| Timeline | Tight deadline | Normal | Flexible |
| Requirements | Unclear/changing | Mostly clear | Well-defined |
| Traffic | Low/internal | Moderate | High/critical |
| Team | Solo/small | Normal | Large/multiple |
| Reversibility | Easy to change | Moderate | Hard to change |

---

## After User Chooses

Once user selects an approach:

1. Read the chosen explorer's output file
2. Expand implementation_steps into detailed tasks
3. Add file:line references from codebase search
4. Add acceptance criteria for each task
5. Map dependencies between tasks
6. Present as implementation plan

Do NOT proceed to detailed planning until user explicitly chooses.
