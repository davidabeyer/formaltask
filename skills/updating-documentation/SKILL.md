---
name: updating-documentation
description: Guide README.md updates based on doc-guard suggestions. This skill should
  be used when updating documentation, fixing docs, addressing doc-guard suggestions,
  or updating README.md. Activates when user requests "update documentation", "fix
  docs", "doc-guard suggestions", or "update README.md".
---

<role>
WHO: Documentation executor
ATTITUDE: Pending suggestions rot fast. Process them now or delete them.
</role>

<purpose>
Your job is to turn doc-guard suggestions into actual README.md updates. Check pending, review each, apply with correct anchors, verify, clear.
</purpose>

## Documentation Structure

| File | Audience | Content |
|------|----------|---------|
| README.md | Humans | Full, detailed documentation |
| CLAUDE.md | AI agents | Concise quick reference |

**YOU MUST UPDATE README.md FILES, NOT CLAUDE.md FILES.**

---

## Workflow

### 1. Check Pending

```bash
./hooks/cli/doc_guard_cli.py pending
```

- **No suggestions:** Ask user what to update
- **Suggestions exist:** Review each

### 2. Review Each Suggestion

For each in pending.json:
1. Read suggested file (usually README.md)
2. Locate section
3. Verify content aligns with implementation

### 3. Apply Updates

Follow anchor conventions from [anchor-conventions.md](references/anchor-conventions.md).

### 4. Verify

- Markdown formatting valid
- Anchor references work
- Command examples tested
- Style matches existing docs

### 5. Clear

```bash
./hooks/cli/doc_guard_cli.py clear
```

---

## References

- [anchor-conventions.md](references/anchor-conventions.md) - Formatting patterns
- [common-updates.md](references/common-updates.md) - Patterns for new patterns, commands, hooks
- [best-practices.md](references/best-practices.md) - Quality guidelines
- [doc-guard-integration.md](references/doc-guard-integration.md) - Workflow and pending.json structure

<rules>
- README.md only - CLAUDE.md is for agents
- Verify before clearing - don't mark done until actually done
- Match existing style - consistency matters
- Test command examples - broken docs are worse than no docs
</rules>
