# Skill Validation Checklist

Validate before considering a skill complete.

## Required Elements (All Tiers)

- [ ] **YAML frontmatter** present and valid
  - [ ] `name:` matches directory name
  - [ ] `name:` uses lowercase-hyphens-only, ≤64 chars
  - [ ] `description:` ≤1024 chars, third person
  - [ ] `description:` includes specific trigger phrases

## Naming & Description

- [ ] Directory uses lowercase with hyphens (e.g., `reviewing-code`)
- [ ] Prefer gerund form (verb+-ing): `processing-pdfs`, `analyzing-data`
- [ ] Description specifies clear trigger conditions
- [ ] Description uses third-person ("This skill should be used when...")

## Structure

- [ ] SKILL.md is at `~/.claude/skills/{skill-name}/SKILL.md`
- [ ] SKILL.md body is <500 lines
- [ ] Has "Why This Exists" section
- [ ] Optional resources in proper subdirectories (`scripts/`, `references/`, `assets/`)
- [ ] References are one level deep (no `references/subdir/file.md`)

## Token Efficiency

- [ ] No user-facing documentation (skills are for agents)
- [ ] No setup procedures or time-sensitive info
- [ ] Examples over explanations
- [ ] Large content (>100 lines) extracted to references/

## Testing

- [ ] Description triggers on expected phrases
- [ ] Description doesn't trigger on unrelated queries
- [ ] Scripts execute without errors (if present)
- [ ] References load when expected (if present)

---

## Modal Skills (Additional)

- [ ] **Mode table** with columns: Mode | When | Key difference
- [ ] **Default mode** explicitly stated ("Default to X")
- [ ] **Selection criteria** Claude can evaluate (not vague)
- [ ] **Per-mode workflow** sections exist
- [ ] **Anti-Patterns section** with table format

### Mode Selection Quality

- [ ] Modes are distinct (not just "small/medium/large")
- [ ] Criteria reference observable signals (user says X, file count, stakes)
- [ ] Quick mode exists for trivial cases
- [ ] Deep mode exists for high-stakes cases

---

## Parallel Skills (Additional)

- [ ] **Phase-gated execution** with blocking gates
- [ ] **Handoff pattern** documented (file structure, not inline)
- [ ] **"SINGLE message" rule** stated for subagent spawning
- [ ] **Synthesis algorithm** defined (not "combine results")
- [ ] **Output limits** enforce prioritization

### Persona Quality

- [ ] Each persona answers ONE distinct question
- [ ] Personas are orthogonal (non-overlapping territories)
- [ ] "NOT Your Territory" sections in persona prompts
- [ ] Hard output limits per persona (1 blocker, 3 polish, 3 skipped)

### Synthesis Quality

- [ ] Ranking algorithm defined (by mention count or similar)
- [ ] Confirmation rule (2+ sources for main findings)
- [ ] Conflict detection (contradictions flagged)
- [ ] Gap analysis (what's missing based on goal)
- [ ] Confidence scoring (High/Medium/Low with criteria)

---

## Anti-Pattern Checklist

Verify skill avoids these:

| Anti-Pattern | Check |
|--------------|-------|
| Sequential subagent launches | Must be single message |
| Overlapping personas | Each has distinct territory |
| No default mode | "Default to X" stated |
| Vague synthesis | Algorithm defined, not "summarize" |
| Missing output limits | Hard caps enforced |
| Checklist workflow | Has thinking patterns, not just steps |
