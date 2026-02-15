<review_resolution>
## Review Finding Resolution

**First, view all findings with status:**
```bash
ft review disposition --list   # Shows all findings with P0-P3 priority and resolution status
```

When review findings block task completion:

1. **Fix the issue** - Your first responsibility. ALL findings are yours to fix.
2. **Mark as wontfix** - If legitimately cannot fix (--reason REQUIRED):
   ```bash
   ft review disposition FILE LINE --reason "Pre-existing in legacy code"
   ```
3. **Defer to new task** - If the finding is real but out of scope for YOUR task:
   ```bash
   ft task create-from-finding FILE LINE --title "Fix edge case in session expiry"
   ```
   This creates a critique-gated task with self-review. Another worker picks it up. You continue working.
4. **Escalate to human** - If you're STUCK and need human judgment:
   ```bash
   ft review disposition FILE LINE --reason "Security tradeoff needs architect" --needshuman
   ```
5. **Re-run review** - After fixing, deferring, or marking disposition

**Disposition CLI (--reason REQUIRED):**
```bash
ft review disposition FILE LINE --reason "REASON"              # wontfix, passes gate
ft review disposition FILE LINE --reason "REASON" --needshuman # escalate, blocks for human
ft review disposition --list                                    # show all
ft review disposition --clear FILE LINE                         # remove entry
```

**When to defer vs wontfix:**
- Finding is real AND fixable by another worker → `create-from-finding` (spawns a task)
- Finding is real but NOT worth fixing (pre-existing, false positive) → `disposition --reason`
- Not sure if finding is valid → `disposition --needshuman`

**Valid wontfix reasons:**
- `"Pre-existing in legacy code"`
- `"Will be addressed in separate epic"`
- `"Requires breaking change"`
- `"False positive: <why reviewer was wrong>"`

**Invalid reasons (fix instead):**
- `"Too hard"` / `"No time"` / `"Low priority"` → these will be rejected

**When to use --needshuman:**
Use ONLY when you're stuck and need human judgment:
- Security tradeoffs requiring architect review
- Architectural decisions beyond task scope
- Unclear requirements needing clarification
- Genuinely uncertain if finding is valid

Human sees escalations in `/inbox` and resolves or marks wontfix.
</review_resolution>
