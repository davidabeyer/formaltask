---
name: hunting-dead-code
description: Deep codebase audit hunting unused imports, uncalled functions, unreachable
  branches, and obsolete code. Use when requesting "hunt dead code", "find unused
  code", "antirez cleanup", "what can I delete", or when codebase feels bloated. Maps
  code topology first, then spawns parallel philosophy-driven hunters. For surface-level
  audits, use code-quality-auditor.
argument-hint: <target-module-or-dir>
uses_skill_run: true
spawns_subagents: true
context: fork
---

# Hunting Dead Code

## Target
$ARGUMENTS

## Codebase Shape
!`find ${0:-.} -name "*.py" -maxdepth 2 | head -20`

Comprehend the codebase before deleting from it. Depth over breadth.

## The Philosophy

**Rich Hickey**: "Simplicity is the ultimate sophistication. Removing things is better than adding things."
**antirez**: "The best code is no code. The second best code is code you can delete."

The enemy is not "bad code" - it's **code that serves no purpose**:

| Code Type | Value | Cost |
|-----------|-------|------|
| Called, tested, necessary | HIGH | Justified |
| Called but could be inlined | MEDIUM | Review |
| Never called, kept "just in case" | ZERO | HIGH |
| Commented out "for reference" | NEGATIVE | HIGH |

**Core axiom**: Every line must answer "yes" to: *Does deleting this line break something real?*

---

## Anti-Patterns We Hunt

### The Import Graveyard
```python
# BAD: Imports that serve no purpose
import os  # Never used
from typing import Optional, List, Dict, Tuple  # Only Optional used
import json  # Was used, now isn't
from .utils import helper_a, helper_b, helper_c  # Only helper_a called
```

### The Orphan Function
```python
# BAD: Functions that nobody calls
def calculate_legacy_price(item):
    """Used to be called from checkout, but checkout was rewritten."""
    return item.price * 0.9

def _internal_helper():
    """Helpers that help nothing."""
    pass
```

### The Unreachable Branch
```python
# BAD: Code that can never execute
def process(status):
    if status == "active":
        return handle_active()
    elif status == "pending":
        return handle_pending()
    else:
        # This branch: status is validated upstream, can only be active/pending
        return handle_unknown()  # DEAD CODE
```

### The Feature Fossil
```python
# BAD: Features that will never ship
if settings.ENABLE_NEW_CHECKOUT:  # Always False in prod
    return new_checkout_flow()
return old_checkout_flow()

# Also BAD: Feature was shipped, flag never removed
if settings.ENABLE_V2_API:  # Always True for 2 years
    return v2_handler()
return v1_handler()  # DEAD CODE
```

### The Commented Corpse
```python
# BAD: "I might need this later" (you won't)
def calculate_total(items):
    # Old implementation - keeping for reference
    # total = 0
    # for item in items:
    #     if item.is_discounted:
    #         total += item.price * 0.9
    #     else:
    #         total += item.price
    # return total

    return sum(get_price(item) for item in items)
```

### The Dead Parameter
```python
# BAD: Parameters that are never used
def create_user(name, email, legacy_id=None, migration_flag=False):
    # legacy_id and migration_flag: added during migration, never removed
    return User(name=name, email=email)
```

---

## Workflow

Steps declare dependencies via `consumes`/`produces` frontmatter.
Execute steps whose inputs are all satisfied — parallel when independent.

| Step | Consumes | Produces | Notes |
|------|----------|----------|-------|
| clarification | user-request | hunt-target, hunt-focus | |
| topology | hunt-target | code-topology | |
| hunt | hunt-target, code-topology | hunt-findings | fan_out: 4 hunters |
| adversarial | hunt-findings | verified-findings | full only |
| synthesis | verified-findings, code-topology | synthesis-report | |

→ Execute in dependency order. For each step:
  1. Read `~/.claude/skills/hunting-dead-code/steps/<name>.md`
  2. Complete it fully before reading the next step

---

## Hunter Philosophies

| Hunter | Question | Hunts For |
|--------|----------|-----------|
| **Import** | "Is this import used?" | Unused imports, redundant imports, `import *` |
| **Function** | "Does anything call this?" | Zero-caller functions, dead utility helpers |
| **Branch** | "Can this path execute?" | Unreachable else, always-true flags, impossible exceptions |
| **Artifact** | "Does this serve a purpose?" | Commented code, dead parameters, stale TODOs |

---

## Output Philosophy

**Never hide findings.** If there are 50 dead imports, report 50 dead imports.

Each hunter reports:
- **Kill** - High confidence deletions
- **Suspect** - Probably dead, needs verification
- **Keep** - False positives (for calibration)

**Prioritization via ranking, not filtering.** Mark highest-confidence as CRITICAL.
**Quality gate:** Only flag what you can prove is dead with grep evidence.

---

## Quality Criteria

| Criterion | Live Code | Dead Code |
|-----------|-----------|-----------|
| Callers | Has callers in production paths | No callers anywhere |
| Tests | Tested or tests something | Not tested, tests nothing |
| Reachability | Can execute from entry point | No path from entry point |
| Recency | Modified recently | Untouched for months/years |
| Documentation | Referenced in docs | No documentation |
| Exports | In `__all__` or public API | Internal and unused |

---

## Safety Rails

**NEVER recommend deleting without verification:**

1. **Dynamic dispatch** - `getattr(obj, method_name)()` can call anything
2. **Plugin systems** - Registered handlers may not have direct callers
3. **Serialization** - Fields used by JSON/pickle may look unused
4. **CLI/Config** - Code called by external configuration
5. **Public API** - Other repos may depend on it
6. **Test fixtures** - May look unused but are pytest magic

**When in doubt, mark as SUSPECT, not KILL.**

---

## Protocols
!`cat ~/.claude/skills/_shared/adversarial-verify.md`
!`cat ~/.claude/skills/_shared/synthesis.md`
!`cat ~/.claude/skills/_shared/review.md`

## References

- [auditor-prompts.md](references/auditor-prompts.md) - Full subagent prompts
- [hickey-simplicity.md](references/hickey-simplicity.md) - Rich Hickey's simplicity philosophy
- [antirez-deletion.md](references/antirez-deletion.md) - antirez on removing code

---
