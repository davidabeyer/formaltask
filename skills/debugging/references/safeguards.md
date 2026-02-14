# Critical Safeguards

## Red Flags Indicating Process Violation

### Phase 1 Violations
- "Let me try this quick fix" without investigation
- Skipping error message reading ("I know what's wrong")
- Not reproducing consistently ("It worked once")

### Phase 2 Violations
- "No time to find working examples"
- Incomplete comparison ("Looks the same to me")
- Ignoring small differences ("That can't matter")

### Phase 3 Violations
- Testing multiple changes simultaneously
- "Probably works now" without verification
- Vague hypothesis ("Something with the config")

### Phase 4 Violations
- Implementing fix without test first
- Adding multiple changes "to be sure"
- Attempting 4th+ fix without architectural discussion

## When You Catch Yourself...

| Violation | Correct Response |
|-----------|------------------|
| Proposing fix without Phase 1-3 | Stop. Complete investigation first. |
| "Let's try this and see" | Stop. Form testable hypothesis first. |
| Third fix attempt failing | Stop. Discuss with team, question architecture. |
| Skipping test creation | Stop. Write failing test first. |
| Multiple simultaneous changes | Stop. Test one variable at a time. |

## Common Mistakes

### Mistake 1: Jumping to Solutions
**Symptom:** Proposing fixes in first response
**Why it's wrong:** No investigation = wrong fix
**Correct approach:** Complete Phase 1-3 before mentioning fixes

### Mistake 2: Testing Multiple Variables
**Symptom:** "Let's change X, Y, and Z to see what happens"
**Why it's wrong:** Can't identify which change worked
**Correct approach:** Change one variable, test, verify, repeat

### Mistake 3: Accepting Partial Understanding
**Symptom:** "It works now, not sure why"
**Why it's wrong:** Problem will reoccur
**Correct approach:** Continue investigation until root cause is clear

### Mistake 4: Infinite Patching
**Symptom:** Attempting 4th, 5th, 6th fixes
**Why it's wrong:** Indicates fundamental misunderstanding
**Correct approach:** Stop at 3 failures, discuss architecture

### Mistake 5: Skipping Test Creation
**Symptom:** Implementing fix without regression test
**Why it's wrong:** Bug can return undetected
**Correct approach:** Write failing test, then fix, verify test passes
