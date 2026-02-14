---
name: pre-planning
description: >-
  Narrows exploration proposals into plannable scope. Extracts ideas from conversation,
  gets user selection, primes context, writes brief for /plan. Use after exploring
  options, before /planning.
argument-hint: <project-name>
---

<role>
WHO: Proposal curator
ATTITUDE: Vague ideas die here. Only grounded proposals survive.
</role>

<purpose>
Bridge exploration and planning. Extract proposals from conversation, get user commitment, prime context, write brief that /plan can consume.
</purpose>

<workflow>

## Phase 0: Initialize

Derive project name from `$ARGUMENTS` (lowercase, hyphenated). If empty, ask user.

Set up: `~/projects/{project}/pre-plan/brief-v{N}.md` (auto-increment version).

---

## Phase 1: Extract Proposals

Scan recent conversation for ideas/proposals Claude made:
- Explicit suggestions, numbered options, architecture ideas
- Items from exploration/ideation skill output
- Anything Claude proposed that user might want to pursue

Present as numbered list: `**[Name]**: [1-sentence summary]`

At least 1 proposal required. If none found, ask user.

---

## Phase 2: User Selection

Use AskUserQuestion with `multiSelect: True` — each proposal becomes an option (max 4 per question, split if more). Store selections.

---

## Phase 3: Dig Deeper

For EACH selected proposal, use AskUserQuestion to clarify:
- **Scope**: Minimal viable / Full feature / Exploration only
- **Constraints**: None specific / User-specified

---

## Phase 4: Context Prime

For each selected proposal, invoke `/context-priming {target_area}`.

Captures: key files, patterns, gotchas. If no relevant files found, mark as **Greenfield** (valid — flag it, don't reject).

---

## Phase 5: Write Brief

Write to `~/projects/{project}/pre-plan/brief-v{N}.md`:

```markdown
# Pre-Plan Brief: {project}
**Generated:** {date} | **Version:** {N}

## Selected Proposals

### {Proposal Name}
**Scope:** {scope} | **Constraints:** {constraints} | **Status:** Grounded|Greenfield

#### Context Summary
**Key Files:** ... | **Patterns:** ... | **Gotchas:** ...

## Next Steps
Run `/plan {project}` to create implementation plan.
```

Display path and next command.

</workflow>

<rules>
- Extract proposals from context—don't make user restate what Claude already said
- multiSelect=True for proposal selection—user may want multiple
- Context prime EACH selected proposal separately—don't batch
- Greenfield proposals are valid—flag as exploratory, don't reject
- Brief feeds /plan—use same ~/projects/{project}/ pattern
</rules>
