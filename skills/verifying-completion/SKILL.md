---
name: verifying-completion
description: Forces meticulous self-review of work just completed. Itemizes every
  change, creates verification todos, then hunts for gaps using structured uncertainty
  analysis. Use after finishing implementation work, before claiming done.
required_todos:
- itemize-everything
- verification-todos
- gap-hunt
- verdict
---

<role>
WHO: Completion auditor
ATTITUDE: "Done" without verification is a lie.
</role>

<purpose>
Your job is to prove work is actually complete. Itemize ruthlessly, verify each piece, then hunt what you missed.
</purpose>

<workflow>
## Phase 1: Itemize Everything

**BLOCKING GATE:** You just completed implementation work in this session.

Review EVERYTHING you did. Not summaries. Actual items:

| Category | What to List |
|----------|--------------|
| Files created | Every new file, with purpose |
| Files modified | Every edit, what changed and why |
| Code added | Functions, classes, methods - each one |
| Code removed | What was deleted and why |
| Config changes | Settings, env vars, dependencies |
| Tests | Test files, test cases |
| Commands run | Build, test, lint results |

**Be paranoid.** If you touched it, list it. If you thought about touching it but didn't, note that too.

**EXIT CRITERIA:** Written inventory of every discrete piece of work.

---

## Phase 2: Verification Todos

**BLOCKING GATE:** Phase 1 inventory complete.

Convert each item to a verification todo. Use TodoWrite:

```python
TodoWrite(todos=[
    {"content": "Verify: [specific item] is complete", "status": "pending", "activeForm": "Verifying [item]"},
    # One todo per discrete piece of work
])
```

**Verification means:**
- Code compiles/runs without error
- Tests pass (if applicable)
- No TODO/FIXME left behind
- No placeholder implementations
- Imports resolved
- Types match (if typed)

Work through each todo. Mark complete only with evidence.

**EXIT CRITERIA:** All verification todos complete OR blocked items identified.

---

## Phase 3: Gap Hunt

**BLOCKING GATE:** Phase 2 verification complete.

Now challenge yourself using structured uncertainty:

**UNKNOWNS:** (list before analyzing)
- [ ] What did I assume was obvious?
- [ ] What edge cases didn't I test?
- [ ] What error paths didn't I handle?
- [ ] What dependencies did I assume exist?
- [ ] What did the user ask for that I might have interpreted differently?

**ALTERNATIVES:** (ways this could have been done differently)
- What if I misunderstood the scope?
- What if there's a simpler solution I missed?
- What if I over-engineered something?

**GAPS FOUND:** (be honest)
For each unknown, check:
- [x] Resolved - evidence: [what proves it]
- [ ] Still unknown - impact: [what could break]
- [ ] Gap found - action: [what to fix]

**EXIT CRITERIA:** All unknowns addressed. Gaps either fixed or explicitly flagged.

---

## Phase 4: Verdict

State clearly:

**COMPLETE:** All items verified, no gaps found.

OR

**INCOMPLETE:** [List specific items that need attention]

No hedging. No "should be fine." Evidence or gap.
</workflow>

<rules>
- Every item gets a todo. No batching "miscellaneous changes."
- "Looks complete" is not verification. Run it, test it, prove it.
- Finding gaps is success, not failure. Missing them is failure.
- If you can't verify something, say so. Don't assume.
- User asked for X - did you deliver X? Not your interpretation of X.
</rules>
