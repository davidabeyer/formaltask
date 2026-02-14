---
name: reviewing-epics
description: 'Thorough two-phase epic review: AC verification then quality review.
  Use when user requests "/epic-review", "review epic", "is this epic done", or when
  verifying completed epics. Phase 1 gates Phase 2.'
argument-hint: <epic-name>
allowed-tools: Bash, Read, Glob, Grep, Task, mcp__auggie-mcp__codebase-retrieval,
  mcp__morph-mcp__warpgrep_codebase_search
see_also:
- /review
- /review-fix
- critique
uses_skill_run: true
required_todos:
- locate-epic
- ac-verification-blocking
- quality-review-parallel
- synthesize
---

<role>
WHO: Epic completion auditor
ATTITUDE: Don't waste time reviewing quality if acceptance criteria weren't met. Phase 1 gates Phase 2.
</role>

<purpose>
Your job is to verify epic completion in two phases:
1. AC verification (>80% required to proceed)
2. Quality review (3 core + 0-3 specialist agents)
</purpose>

<workflow>

---

## Phase 0: Locate Epic

1. Query database: `ft task list {epic-name}`
2. If found, check for specs at:
   - `.plans/{epic-name}-specs/*-spec.yaml`
   - `~/projects/{epic-name}/.plans/{epic-name}-specs/*-spec.yaml`
3. Read specs to get acceptance criteria per task

**Gate:** Epic file found with parseable AC list.

---

## Phase 1: AC Verification (BLOCKING)

Spawn single opus agent to verify each acceptance criterion.

```python
# Build AC list for verification
ac_list = []
for task in tasks:
    if task["criteria"]:
        ac_list.append(f"\n### Task #{task['id']}: {task['title']}")
        for i, ac in enumerate(task["criteria"], 1):
            ac_list.append(f"- AC{i}: {ac}")

ac_text = "\n".join(ac_list)

Task(
    subagent_type="acceptance-verifier",
    model="opus",
    description="Verify acceptance criteria",
    prompt=f"""# AC Verification: {epic_name}

{ac_text}  # Built from tasks[].criteria

For each AC:
- PASS: Clear evidence criterion was met
- FAIL: No evidence or partial implementation
- SKIP: Not verifiable from code

Verify against `origin/master` (fetch first), not local checkout.

ALSO verify for each task:
- PR merged to master (not just DB status = completed)
- If PR open/missing, mark all that task's ACs as FAIL with "PR not merged"

Output JSON with pass_rate and failed_criteria list.
"""
)
```

**Gate:** If pass_rate < 0.80, STOP. Skip Phase 2. Write synthesis with:
- Verdict: BLOCKED
- Blockers: failed criteria list
- Recommendation: "Fix blockers, re-run /reviewing-epics"

---

## Phase 2: Quality Review (PARALLEL)

**Only runs if Phase 1 passes (>80% AC verification).**

### Agent Selection

```python
# Core agents (always run)
core_agents = ["code-reviewer", "simplifying-code", "test-quality-auditor"]

# Specialist agents based on required_reviews metadata
REVIEW_TO_AGENT = {
    "security": "path-security-reviewer",
    "perf": "performance-auditor",
    "sqlite": "sqlite-reviewer",
    "subprocess": "subprocess-reviewer",
    "hooks": "hook-reviewer",
    "schema": "schema-reviewer",
    "state-machine": "state-machine-reviewer",
}

# Collect from all tasks' metadata.required_reviews
specialists = [REVIEW_TO_AGENT[r] for r in all_reviews if r in REVIEW_TO_AGENT]
```

**Hard limits per agent:** 1 Blocker, 2 High, 2 Medium

---

## Phase 3: Synthesize

Aggregate findings by task. Determine verdict:
- **APPROVED** - 0 blockers
- **FIX_AND_SHIP** - 1-2 blockers
- **BLOCKED** - 3+ blockers

**If APPROVED:** Run `ft epic update {epic-name} --reviewed` to record review timestamp.

---

</workflow>

<output>
Format: Epic review report with AC verification + quality findings by task
Location: `~/projects/{project}/reviewing-epics/reports/`
Success: Clear APPROVED/FIX_AND_SHIP/BLOCKED verdict with task-grouped findings
</output>

<rules>
- Phase 1 gates Phase 2 - don't review quality if AC fails (<80%)
- Every acceptance criterion gets checked
- Hard limits per agent (1 blocker, 2 high, 2 medium)
- Findings tied to specific tasks, not floating
- Include "What's Good" section - celebrate wins
</rules>

## References

- [quality-agent-prompts.md](references/quality-agent-prompts.md) - Agent prompts
- [epic-review-report-template.md](references/epic-review-report-template.md) - Report template
