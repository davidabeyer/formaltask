# Documentation Patterns

Opinionated rules for README.md vs CLAUDE.md placement and content.

---

## Core Constraint

**CLAUDE.md autoloads** whenever Claude reads ANY file in that directory.

This means:
- Every line in CLAUDE.md costs tokens on every file read
- Bloated CLAUDE.md = bloated context = worse Claude performance
- CLAUDE.md is for **mistake prevention**, not documentation

---

## The Two-File System

| File | Purpose | Constraint | Audience |
|------|---------|------------|----------|
| README.md | Full documentation | Package boundaries only | Humans |
| CLAUDE.md | Gotchas/footguns | **<50 lines** | Claude |

**Relationship:** CLAUDE.md prevents mistakes. README.md explains everything else.

---

## README.md Rules

### When Required

1. **Has package manifest** - `pyproject.toml`, `setup.py`, `package.json`
2. **Passes standalone test** - Could use this directory without parent

### When Forbidden

| Location | Why |
|----------|-----|
| `cli/`, `commands/` | Internal implementation |
| `utils/`, `helpers/` | Internal utilities |
| `tests/`, `test/` | Test infrastructure |
| `.github/`, `.vscode/` | Config, not code |
| `__pycache__/`, `node_modules/` | Generated |

### Structure (Required Sections)

```markdown
# {Module Name}

{One paragraph: what and why}

## Quick Start

{Copy-pasteable example}

## Usage

{Use cases with working examples}

## API Reference

{Only if >5 public functions}

## See Also

{Only if real cross-references exist}
```

### Style

| Do | Don't |
|----|-------|
| Working examples with real values | Pseudo-code, `foo`, `bar` |
| Explain WHY, not just WHAT | API dump without context |
| Copy-pasteable code | Code that needs modification |
| Edge cases and gotchas | Assume obvious behavior |

---

## CLAUDE.md Rules

### The 50-Line Rule

**Maximum 50 lines. No exceptions.**

If you need more, either:
1. The gotchas belong in README.md
2. The code is too complex (simplify it)

### When Required

1. Has documented gotchas (≥1 footgun)
2. Claude makes mistakes here without guidance

### When Forbidden

1. No gotchas identified → delete the file
2. Code is self-explanatory → delete the file
3. Would just duplicate README → delete the file

### Structure (Strict Template)

```markdown
# {module}/ CLAUDE.md

{Purpose - ONE sentence, max 15 words}

## Gotchas

- {Footgun 1}
- {Footgun 2}

## See Also

- `README.md` - Full documentation
```

That's it. Nothing else.

### Content Rules

| Allowed | Forbidden |
|---------|-----------|
| One-sentence purpose | Paragraphs of explanation |
| Bullet-point gotchas | Tables >5 rows |
| Link to README | Code blocks >3 lines |
| Link to related CLAUDE.md | API documentation |
| | Usage examples |
| | Architecture diagrams |
| | "Quick reference" tables |

### The Gotcha Test

For each bullet point, ask: **Would Claude make a mistake without this?**

- YES → Keep it
- NO → Delete it

---

## Subdirectory Documentation

When a directory doesn't get its own README, document it as a **section in parent**.

### Section Template

```markdown
## {Subdir Name} (`{subdir}/`)

{2-3 sentences: what and why}

### Key Components

| Component | Purpose |
|-----------|---------|
| `{file}` | {what} |

### Usage

{Brief example if needed}
```

### Example

In `formaltask/README.md`:

```markdown
## Validators (`validators/`)

PreToolUse validators that enforce project rules.

### Available Validators

| Validator | Enforces |
|-----------|----------|
| `TDDValidator` | Test-first development |
| `DocGuardValidator` | Documentation updates |
| `StubDetector` | No placeholder code |

### Creating a Validator

Inherit from `BaseValidator`, implement `validate()`.
See `tdd_validator.py` for example.
```

---

## Cross-Reference Pattern

### README → CLAUDE.md

Don't. README is comprehensive; it doesn't need to point to the summary.

### CLAUDE.md → README

Always:
```markdown
## See Also

- `README.md` - Full documentation
```

### Code → Documentation

```python
"""Brief docstring.

See README.md#section for full documentation.
"""
```

---

## Anti-Patterns

### README.md

| Anti-Pattern | Fix |
|--------------|-----|
| Wall of text | Headings, bullets, tables |
| API without context | Explain when to use |
| Stale examples | Verify examples work |
| "See code" | Document the details |
| Empty sections | Delete them |

### CLAUDE.md

| Anti-Pattern | Fix |
|--------------|-----|
| >50 lines | Ruthlessly cut |
| Duplicates README | Delete, link instead |
| Explanatory prose | Bullet points only |
| "Quick reference" tables | Move to README |
| No actual gotchas | Delete the file |
| Generic information | Only footguns |

---

## Enforcement Checklist

Before committing documentation:

### README.md
- [ ] At package boundary (has manifest or passes standalone test)?
- [ ] Not in forbidden location?
- [ ] Has required sections (purpose, quick start, usage)?
- [ ] Examples actually work?
- [ ] No empty sections?

### CLAUDE.md
- [ ] ≤50 lines?
- [ ] Has at least 1 real gotcha?
- [ ] No code blocks >3 lines?
- [ ] No tables >5 rows?
- [ ] Links to README?
- [ ] Every bullet passes "mistake test"?

### Neither
- [ ] Covered by parent README section?
- [ ] Or code is self-explanatory (no docs needed)?
