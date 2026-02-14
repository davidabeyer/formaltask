# Skill Creation Step-by-Step Guide

## Step 1: Understanding the Skill with Concrete Examples

Skip only when usage patterns are already clearly understood.

To create an effective skill, gather concrete examples of how it will be used. Ask:

- "What functionality should this skill support?"
- "Can you give examples of how this skill would be used?"
- "What would a user say that should trigger this skill?"

Avoid overwhelming users with too many questions at once. Conclude when there's a clear sense of functionality.

## Step 2: Planning Reusable Contents

Analyze each example by:

1. Considering how to execute from scratch
2. Identifying what scripts, references, and assets would help when executing repeatedly

**Example analyses:**

| Skill | Query | Analysis | Resource |
|-------|-------|----------|----------|
| `pdf-editor` | "Rotate this PDF" | Same code rewritten each time | `scripts/rotate_pdf.py` |
| `frontend-builder` | "Build me a todo app" | Same boilerplate each time | `assets/hello-world/` |
| `big-query` | "How many users logged in?" | Schema rediscovery each time | `references/schema.md` |

## Step 3: Initializing the Skill

Skip if iterating on an existing skill.

**Create the skill:**

```bash
# Create directory
mkdir -p ~/.claude/skills/{skill-name}

# Create SKILL.md with frontmatter
cat > ~/.claude/skills/{skill-name}/SKILL.md << 'EOF'
---
name: {skill-name}
description: >-
  {Action verbs} {outputs}. Use when {trigger phrases},
  {file types}, or {contexts}.
---

# {Skill Title}

## Why This Exists

{Problem statement}
EOF

# Create optional resource directories
mkdir -p ~/.claude/skills/{skill-name}/{scripts,references,assets}
```

**DO NOT:**
- Create zip files or packages
- Use init/package scripts
- Place skills anywhere other than `~/.claude/skills/`

The skill is ready immediately once SKILL.md is created.

## Step 4: Edit the Skill

Remember: the skill is for another Claude instance to use. Focus on information that would be beneficial and non-obvious.

### 4.1 Create Reusable Resources First

Start with `scripts/`, `references/`, and `assets/` identified in Step 2. This may require user input (e.g., brand assets, schemas, templates).

Delete any example files not needed for the skill.

### 4.2 Update SKILL.md

**Writing style:** Use imperative/infinitive form (verb-first instructions), not second person. Use objective, instructional language.

Answer these questions in SKILL.md:
1. What is the purpose (few sentences)?
2. When should the skill be used?
3. How should Claude use the bundled resources?

## Step 5: Validate the Skill

See [validation-checklist.md](validation-checklist.md) for the complete checklist.

## Step 6: Iterate

After testing, users may request improvements.

**Iteration workflow:**
1. Use the skill on real tasks
2. Notice struggles or inefficiencies
3. Identify SKILL.md or resource updates needed
4. Implement changes and test again
