<documentation>
## Documentation Required

This task requires documentation updates. Follow these guidelines:

**Decision tree:**
1. Changed public API/CLI → Update README.md (or section in parent README)
2. Added footgun/gotcha → Update CLAUDE.md
3. Internal refactor, same behavior → No doc change needed

**What NOT to document:**
- Implementation details (code is source of truth)
- Obvious behavior from function names
- Anything you'd delete on review

**File purposes:**

| File | Content | Constraint |
|------|---------|------------|
| `README.md` | How to use, examples, why | Package boundaries only |
| `CLAUDE.md` | Gotchas that cause bugs | <50 lines, no prose |

**CLAUDE.md test:** Would Claude make a mistake without this info? If no → don't add it.

**README.md test:** Would deleting this let a real misunderstanding slip through? If no → delete it.
</documentation>
