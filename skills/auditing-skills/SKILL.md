---
name: auditing-skills
description: Audits skills against spec with line-level findings. Use when "audit
  skill", "fix skill", or after skill review. For creating new skills, use creating-skills.
uses_skill_run: true
required_todos:
- load-context
- structural-audit
- language-audit
- agent-audit
- build-system-audit
---

<role>
WHO: Skill compliance enforcer
ATTITUDE: Broken skills waste tokens. Pass or fail.
</role>

<purpose>
Your job is finding every violation. Read skill, check against spec, report with line numbers. No summaries.
</purpose>

## Phase 1: Load Context

**BLOCKING GATE:** Skill name provided.

```python
# 1. Read the skill
skill_path = Path.home() / ".claude/skills" / skill_name / "SKILL.md"
content = Read(skill_path)

# 2. Load build config
config = Read(Path.home() / ".claude/skills/_config.yaml")

# 3. Check which pattern matches
# auditing-* → inherit: [defaults, output-paths, subagent-spawn], tools: [auggie, warpgrep], uses_skill_run: true
# reviewing-* → inherit: [defaults, output-paths], tools: [auggie, warpgrep], uses_skill_run: true
# hunting-* → same as auditing-*
# etc.

# 4. Load creating-skills spec for reference
spec = Read(Path.home() / ".claude/skills/creating-skills/SKILL.md")
```

**EXIT CRITERIA:** Skill content, config, and spec loaded.

---

## Phase 2: Structural Audit

Check each section exists and follows spec:

| Section | Required Format | Line Check |
|---------|-----------------|------------|
| Frontmatter | `name`, `description` in YAML | Lines 1-N |
| `<role>` | WHO (2-4 words) + ATTITUDE (≤10 words, consequence) | Must exist |
| `<purpose>` | "Your job is [punch]. [Consequence.]" | Must start with "Your job" |
| `<workflow>` OR phases | Numbered steps or Phase N with gates | Must exist |
| `<rules>` | Bullet points, consequences not explanations | Must exist |

**Report format:**
```
P1 STRUCTURAL: Line 8 - <role> missing ATTITUDE
P2 STRUCTURAL: Line 15 - <purpose> starts with "This skill" not "Your job"
```

---

## Phase 3: Language Audit

Scan for violations:

| Violation | Pattern | Severity |
|-----------|---------|----------|
| Third person | "This skill", "It will" | P1 |
| Passive voice | "should be used", "can be done" | P2 |
| Hedge words | "might", "could", "perhaps", "consider" | P2 |
| Filler | "basically", "essentially", "in order to" | P3 |
| Explanation not consequence | Long sentences explaining why | P2 |

```python
VIOLATIONS = {
    r'\bThis skill\b': ('P1', 'Third person - use "Your job"'),
    r'\bIt will\b': ('P1', 'Third person'),
    r'\bshould be\b': ('P2', 'Passive voice'),
    r'\bmight\b': ('P2', 'Hedge word'),
    r'\bcould\b': ('P2', 'Hedge word'),
    r'\bperhaps\b': ('P2', 'Hedge word'),
    r'\bconsider\b': ('P2', 'Hedge word - use imperative'),
    r'\bbasically\b': ('P3', 'Filler word'),
    r'\bessentially\b': ('P3', 'Filler word'),
    r'\bin order to\b': ('P3', 'Filler - just use "to"'),
}
```

---

## Phase 4: Agent Audit

**P0 BLOCKERS** - skill will crash:

```python
# 1. Find all subagent_type references
agents_used = re.findall(r'subagent_type="([^"]+)"', content)

# 2. Check each exists
existing = [f.stem for f in (Path.home() / ".claude/agents").glob("*.md")]
builtins = {"Explore", "general-purpose", "Bash", "Plan"}

for agent in agents_used:
    if agent not in existing and agent not in builtins:
        report(f"P0 AGENT: Missing agent '{agent}' - skill will crash")
    if agent == "general-purpose":
        report(f"P1 AGENT: Uses generic 'general-purpose' - create specialized agent")
```

**Subagent prompt check:**

```python
# Find Task() calls and check prompts have required fields
REQUIRED = ["SCOPE", "CONTEXT", "TASK", "OUTPUT", "DONE WHEN"]
# Or at minimum: specific file refs, prior findings, deliverable, output path
```

---

## Phase 5: Build System Audit

```python
# 1. Which pattern should match?
patterns = {
    "auditing-*": {"inherit": ["defaults", "output-paths", "subagent-spawn"],
                   "tools": ["auggie", "warpgrep"],
                   "frontmatter": {"uses_skill_run": True}},
    "reviewing-*": {"inherit": ["defaults", "output-paths"], ...},
    # etc from _config.yaml
}

# 2. Check injections present
if matches_pattern("auditing-*"):
    if "<!-- @tools-injected -->" not in content:
        report("P2 BUILD: Missing @tools-injected - run build")
</rules>
