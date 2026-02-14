---
consumes: [user-request]
produces: [doc-verdict]
---
# Phase 0: Necessity Check

Before creating documentation, apply the decision trees from the Documentation Architecture section in SKILL.md.

## Actions

Write to `{run.run_dir}/00-necessity-check.md`:
- README.md verdict and target path
- CLAUDE.md verdict (gotchas or not needed)

## Decision Trees

### README.md: When Required

- Has package manifest (pyproject.toml, package.json) → **Required**
- Passes standalone test (usable without parent) → **Required**
- Otherwise → Section in parent README, not own file
- **FORBIDDEN:** `cli/`, `utils/`, `tests/`, `.github/` dirs

### CLAUDE.md: When Required

- Has gotchas (things that cause bugs) → **Required** (max 50 lines)
- Claude makes mistakes here without guidance → **Required**
- Otherwise → Don't create one

## Gate

**If neither is needed:** Stop. Don't create documentation for documentation's sake.
