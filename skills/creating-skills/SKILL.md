---
name: creating-skills
description: MUST BE USED when creating Claude Code skills. Activates on "create skill",
  "new skill", "skill creator", or when building workflow automation.
required_todos:
- meta-analysis
- discovery-divergent
- adversarial-pre-ship
- self-critique
- final-gate-checkpoint
---

# Creating Skills

Your job is to create skills that work on first load. Direct, punchy, no fluff.

---

## BLOCKING GATE: Punchiness Requirements

**Read this BEFORE writing ANY skill content. Violations = rewrite.**

### Line Limits (HARD)

| Type | Limit | Exception |
|------|-------|-----------|
| Skill | **200 lines** | Complex multi-phase with references/ can exceed |
| Agent | **100 lines** | 50-80 ideal |

### Voice (NON-NEGOTIABLE)

| Element | Rule | Example |
|---------|------|---------|
| WHO | 2-4 word noun phrase | "Documentation archaeologist" not "A systematic documentation expert who..." |
| ATTITUDE | ≤10 words, states consequence | "Existing docs are lies." not "We should treat existing docs with skepticism" |
| Purpose | "Your job is [punch]." | Not "This skill helps with..." |
| Rules | Consequence, not explanation | "Sequential defeats parallel." not "Running things in sequence is slower than parallel" |

### Anti-Verbosity Checklist

Before writing, ask:
- [ ] Can I delete this sentence? → Delete it.
- [ ] Can I replace this paragraph with a table? → Use table.
- [ ] Does this explain HOW to think? → Delete. Skills say WHAT, not HOW.
- [ ] Is this a template Claude could generate? → Delete.

**EXIT GATE:** If skill draft exceeds line limit → cut ruthlessly before proceeding.

---

## Phase -1: Meta-Analysis (MANDATORY)

```xml
<meta_analysis>
  <stated_request>[User wants skill for X]</stated_request>
  <real_need>[What workflow problem are they ACTUALLY solving?]</real_need>
  <skill_vs_alternatives>
    <could_be_agent>[Skills orchestrate, agents do focused work]</could_be_agent>
    <could_be_hook>[Automatic triggers vs explicit invocation]</could_be_hook>
    <claude_already_knows>[Does Claude do this without a skill?]</claude_already_knows>
  </skill_vs_alternatives>
  <failure_modes>[Ways this skill could fail]</failure_modes>
</meta_analysis>
```

**EXIT:** Confirmed skill is the right solution.

---

## Phase 0: Discovery (MANDATORY)

```python
AskUserQuestion(questions=[
    {"question": "What problem does this skill solve?", "header": "Problem",
     "options": [
         {"label": "Automate repetitive workflow", "description": "Same steps every time"},
         {"label": "Enforce quality gate", "description": "Catch mistakes before they ship"},
         {"label": "Orchestrate multiple agents", "description": "Parallel analysis"},
         {"label": "Domain knowledge injection", "description": "Context Claude doesn't have"}
     ], "multiSelect": False},
    {"question": "What triggers should activate this?", "header": "Triggers",
     "options": [
         {"label": "Explicit command only", "description": "/skill-name"},
         {"label": "Keyword detection", "description": "Phrases like 'review this'"},
         {"label": "After another skill", "description": "Chains from /plan, /commit"}
     ], "multiSelect": True}
])
```

After discovery, explore approaches:
```xml
<divergent>
  <generate>
    - Simple: Just workflow, no agents
    - Modal: Phase 0 scope selection
    - Decomposed: Steps with dependency DAG (only if step B needs output from step A)
    - Parallel: Multiple agents + synthesis
    - Wild: Could this be 5 lines?
  </generate>
</divergent>
```

Pick simplest tier. Upgrade only when proven necessary. Decompose only when steps have **hard ordering** — soft conversational loops stay monolithic.

---

## Structure

```yaml
---
name: gerund-form-name
description: >-
  {Verbs} {outputs}. Use when {triggers}. For X, use {other} instead.
uses_skill_run: true  # If needs output paths
---

<role>
WHO: [2-4 word noun phrase]
ATTITUDE: [≤10 words, consequence]
</role>

<purpose>
Your job is [punch]. [Why this matters.]
</purpose>

<workflow>
## Phase 0: [Name]
[Steps]

## Phase N: Checkpoint (MANDATORY before output)
```xml
<checkpoint>
  <verify>[Did I do X?] [YES/NO]</verify>
  <conclusion>[Metrics]</conclusion>
  <flips_if>[Reversal condition]</flips_if>
</checkpoint>
```
</workflow>

<rules>
- [Punchy constraint]
</rules>
```

---

## Decomposed Skills (steps/ with dependency frontmatter)

**When:** Skill has 3+ phases where later phases need output from earlier ones. NOT for soft-ordered dialogue loops.

Create `steps/` directory. Each step gets YAML frontmatter:

```markdown
---
consumes: [user-request]     # artifacts this step needs
produces: [gathered-data]     # artifacts this step creates
optional: true                # skippable without blocking downstream
---
# Step instructions here
```

Chain artifacts across steps: step A `produces: [X]` → step B `consumes: [X]`. The step gate (PreToolUse hook) enforces ordering automatically.

| Artifact | Always satisfied |
|----------|-----------------|
| `user-request` | Yes — root steps consume only this |

**Example chain:** `clarify` produces `[target]` → `analyze` consumes `[target]`, produces `[findings]` → `report` consumes `[findings]`

**Deep reference:** `docs/architecture/skill-spans.md`

---

## Modal Skills (Phase 0 Scope Selection)

```python
AskUserQuestion(questions=[{
    "question": "What scope for this {skill}?",
    "header": "Mode",
    "options": [
        {"label": "Single file", "description": "Deep analysis of one file"},
        {"label": "Module (Recommended)", "description": "All files in one directory"},
        {"label": "Batch/Custom", "description": "Multiple targets, parallel workers"}
    ], "multiSelect": False
}])
```

**Single file:** Direct execution.
**Module/Batch:** Read `skills/_references/orchestration.md`, spawn workers.

---

## Skills with Task() Calls

| Required in Prompt | Example |
|--------------------|---------|
| SCOPE | `"src/auth/login.py:50-120"` |
| CONTEXT | `"session fixation found"` |
| TASK | `"check refresh_token.py"` |
| OUTPUT | `"write to {outputs}/audit.md"` |
| DONE WHEN | `"both files checked"` |

If Parallel tier: Load `/creating-agents` first.

---

## Adversarial Pre-Ship (MANDATORY)

```xml
<adversarial>
  <future_state>Skill shipped. Used 50 times. Failed 30%.</future_state>
  <failure_pattern_1>[How it broke]</failure_pattern_1>
  <failure_pattern_2>[User invoked wrong]</failure_pattern_2>
  <failure_pattern_3>[Conflicted with other skill]</failure_pattern_3>
  <prevent>[Fix before shipping]</prevent>
</adversarial>
```

---

## Self-Critique (MANDATORY)

| Pass | Check |
|------|-------|
| Role | WHO 2-4 words? ATTITUDE ≤10 words + consequence? |
| Purpose | "Your job is..." ≤10 words? |
| Workflow | Fresh Claude executes without questions? |
| Rules | Each prevents specific failure? |
| Anti-Patterns | No hedge words, passive voice, third person? |

**Output:** `READY` or `NEEDS WORK`.

---

## Final Gate

```xml
<checkpoint>
  <verify>Solves REAL NEED from meta_analysis? [YES/NO]</verify>
  <verify>Adversarial preventions applied? [YES/NO]</verify>
  <verify>Self-critique READY? [YES/NO]</verify>
  <verify>Under line limit? [YES/NO]</verify>
  <conclusion>[Ship or fix]</conclusion>
</checkpoint>
```

### Checklist

**Structural:**
- [ ] `<role>` with WHO + ATTITUDE
- [ ] `<purpose>` starts "Your job is"
- [ ] `<workflow>` with phases
- [ ] `<rules>` with bullets
- [ ] If decomposed: every `consumes` artifact has a matching `produces` upstream

**Voice:**
- [ ] WHO 2-4 words
- [ ] ATTITUDE ≤10 words, consequence
- [ ] No third person, passive, hedge words
- [ ] Second person throughout

**Agent (if Task()):**
- [ ] `subagent_type` references existing agent
- [ ] Prompt includes SCOPE, CONTEXT, TASK, OUTPUT, DONE WHEN
- [ ] `uses_skill_run: true` in frontmatter

**Antirez:**
- [ ] Claude doesn't already know this
- [ ] Not teaching HOW to think
- [ ] **Under line limit**

---

**If any fail:** Fix before shipping.
