# Example Workflows

## Example 1: New Pattern Added

**Situation**: Code added new background worker pattern, doc-guard suggests update

```bash
$ ./hooks/cli/doc_guard_cli.py pending
1 pending suggestion(s):

[1] New background worker for analytics
    -> CLAUDE.md: Key Patterns
      Reason: New fire-and-forget pattern in analytics_worker.py
```

**Actions:**
1. Read `analytics_worker.py` to understand pattern
2. Check if similar to existing `BACKGROUND-WORKERS` pattern
3. Either extend existing pattern or create new anchor
4. Add example showing analytics-specific usage
5. Reference anchor in `analytics_worker.py` docstring
6. Clear suggestions

## Example 2: New Command Added

**Situation**: New CLI command added, needs documentation

```bash
$ ./hooks/cli/doc_guard_cli.py pending
1 pending suggestion(s):

[1] New epic-verify command
    -> CLAUDE.md: Common Commands
      Reason: New command in cli/commands/epic_verify.py
```

**Actions:**
1. Find "Common Commands" section in CLAUDE.md
2. Add command under appropriate subsection:
   ```markdown
   # Verify epic GitHub sync status
   python -m hooks.cli pm epic-verify <epic-name>
   ```
3. Update CLI command reference table if it exists
4. Clear suggestions

## Example 3: Hook Configuration Changed

**Situation**: New PreToolUse hook added

```bash
$ ./hooks/cli/doc_guard_cli.py pending
1 pending suggestion(s):

[1] New websearch-to-exa validator hook
    -> CLAUDE.md: Hook Configuration
      Reason: New PreToolUse hook enforces Exa usage
```

**Actions:**
1. Find "Hook Configuration" section
2. Update PreToolUse hooks table
3. Add to "Project-Specific Rules" if enforced
4. Document in "Common Gotchas" if there are issues
5. Clear suggestions
