<escalation_protocol>
## When to Escalate to Human

**Use your best judgment first.** Only escalate if you ABSOLUTELY cannot proceed without human intervention.

Escalate when ALL of these are true:
1. You have exhausted reasonable approaches (tried 3+ different solutions)
2. The blocker is external to your capabilities (credentials, architecture decisions, ambiguous requirements)
3. Continuing would risk wasted effort or incorrect implementation

**Common escalation scenarios:**
- Need API credentials or secrets you don't have access to
- Target files were deleted/refactored by another task (merge conflicts you can't resolve)
- Security-sensitive changes requiring human sign-off
- Requirements are contradictory and you need clarification
- Test failures persist after 3+ fix attempts with different approaches

**Do NOT escalate for:**
- Things you can figure out by reading code or documentation
- Minor uncertainties where either choice is reasonable
- Problems you haven't actually tried to solve yet

## How to Escalate

Use the CLI command (this registers the block and notifies humans via `/inbox`):

```bash
python3 -m formaltask.cli.pm blocked "<brief description of what's blocking you>"
```

**Examples:**
```bash
python3 -m formaltask.cli.pm blocked "Need OPENROUTER_API_KEY to test LLM integration"
python3 -m formaltask.cli.pm blocked "pm_dashboard.py deleted in Task #2322 - need guidance on new architecture"
python3 -m formaltask.cli.pm blocked "Auth flow unclear - OAuth vs JWT decision needed"
```

**Important:** Human will see blocked workers in `/inbox` and can resolve or provide guidance.

## Report Infrastructure Problems (Without Blocking Yourself)

If something is broken (CI, missing dep, shared config) but you can still work around it, report it instead of blocking:

```bash
ft work report "Fix CI: pytest failures in test_auth after merge"
```

This creates a blocker task for another worker to fix. You **continue working**. One open blocker per epic (dedup). Max 3 reports per task (rate limit).

**Use `ft work report` when:** CI broken on master, shared dependency missing, config issue affecting multiple workers.
**Use `ft work blocked` when:** YOU are stuck and cannot continue.
</escalation_protocol>
