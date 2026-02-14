---
name: documenting-deeply
description: Deep documentation refresh with comprehension before writing. Use when
  requesting "documentation refresh", "update docs for [area]", "document [module]",
  or when docs are stale/missing/incorrect. Maps doc architecture first, understands
  code deeply, then writes accurate documentation. For incremental doc-guard updates,
  use documentation-updater instead.
argument-hint: <target-module-or-dir>
---

# Deep Documentation

Understand code completely before documenting. Depth over breadth.

## Why This Exists

Surface-level documentation produces incorrect or incomplete docs:

- **Skimming fails** - Miss edge cases, special behaviors, design rationale
- **No comprehension** - Can't document what you don't understand
- **Pattern matching** - Grep for function names ≠ understanding behavior
- **Copy-paste docs** - Propagate errors from stale existing docs

This skill enforces **understanding before documenting** through sequential deep dives.

---

## Core Principle

**You cannot document code you don't understand.**

Before writing ANY documentation:
1. Read ALL relevant code (not just entry points)
2. Trace actual execution paths
3. Understand the design intent
4. Consider WHY the code exists this way

Only then document.

---

## The Philosophy (APPLY THIS)

The enemy is **docs that don't earn their keep**:

| Doc Type | Value | Action |
|----------|-------|--------|
| Explains WHY, prevents mistakes | HIGH | Write this |
| Duplicates what code says | ZERO | Delete this |
| Explains obvious behavior | ZERO | Delete this |
| Out of date, misleading | NEGATIVE | Fix or delete |

**The Deletion Test:** For every paragraph ask: *Would deleting this let a real misunderstanding slip through?* If no → delete it.

**The Boredom Test:** Document until confusion transforms into boredom. Then stop.
- Done: New developer could use this without asking questions
- Not done: Same questions keep coming in code reviews

### Output Limits (MANDATORY)

**README.md:**
- **5 sections max** - Purpose, Quick Start, Usage, API (if >5 functions), See Also
- **50 lines per section max** - If longer, you're explaining too much
- **3 code examples max** - One per concept

**CLAUDE.md:**
- **10 gotchas max** - If more, the code is too complex
- **50 lines total** - Already enforced

For each line, ask: *Would deleting this let a real misunderstanding slip through?*
If no → delete it.

---

## Documentation Architecture

> **Antirez Principle:** The best documentation is no documentation.
> The second best is minimal documentation at the right level.

Documentation follows **package boundaries**, not directory structure.

### File Purposes

| File | Purpose | Constraint |
|------|---------|------------|
| `README.md` | Full documentation for humans | Only at package boundaries |
| `CLAUDE.md` | Gotchas to prevent Claude mistakes | **<50 lines**, autoloads on file read |

**Critical:** CLAUDE.md autoloads whenever Claude reads any file in that directory. Keep it minimal or it bloats every operation.

### README.md: When Required

- Has package manifest (pyproject.toml, package.json) → **Required**
- Passes standalone test (usable without parent) → **Required**
- Otherwise → Section in parent README, not own file
- **FORBIDDEN:** `cli/`, `utils/`, `tests/`, `.github/` dirs

### CLAUDE.md: When Required

- Has gotchas (things that cause bugs) → **Required** (max 50 lines)
- Claude makes mistakes here without guidance → **Required**
- Otherwise → Don't create one

See [doc-patterns.md](references/doc-patterns.md) for templates and anti-patterns.

---

## Workflow

Execute phases sequentially. Each step file is self-contained.

1. [Phase 0: Necessity Check](steps/necessity-check.md) — Apply decision trees, write verdict
2. [Phase 1: Documentation Discovery](steps/discovery.md) — Explore subagent maps existing docs
3. [Phase 2: Focus Area Selection](steps/focus-selection.md) — Select area by priority
4. [Phase 3: Deep Comprehension](steps/comprehension.md) — General-purpose subagent reads all code
5. [Phase 4: Gap Analysis](steps/gap-analysis.md) — Compare comprehension to existing docs
6. [Phase 5: Documentation Writing](steps/writing.md) — General-purpose subagent writes drafts
7. [Phase 6: Verification](steps/verification.md) — Adversarial subagent verifies docs match code
8. [Phase 7: Final Output](steps/output.md) — Apply verified docs to actual files

---

## Anti-Patterns

| Don't | Why |
|-------|-----|
| Skim code, write docs | Will miss edge cases, special behaviors |
| Copy existing stale docs | Propagates errors |
| Skip comprehension phase | Can't document what you don't understand |
| Skip verification | Docs may not match code |
| Document without reading ALL code | Miss important details |
| Guess at behavior | Produces incorrect documentation |

---

## When NOT to Use

- **Incremental updates**: Use `documentation-updater` for doc-guard suggestions
- **Trivial changes**: Adding one command to existing docs doesn't need deep dive
- **Pure formatting**: Fixing markdown doesn't require comprehension

---

## References

- [comprehension-phase.md](references/comprehension-phase.md) - Deep reading protocol
- [doc-patterns.md](references/doc-patterns.md) - README vs CLAUDE.md patterns
- [verification-protocol.md](references/verification-protocol.md) - Accuracy verification
- [handoff-protocol.md](references/handoff-protocol.md) - Handoff file requirements
