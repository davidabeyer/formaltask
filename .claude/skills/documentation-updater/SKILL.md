---
name: documentation-updater
description: Guide CLAUDE.md updates based on doc-guard suggestions. This skill should be used when updating documentation, fixing docs, addressing doc-guard suggestions, or updating CLAUDE.md. Activates when user requests "update documentation", "fix docs", "doc-guard suggestions", or "update CLAUDE.md".
version: 1.0.0
---

# Documentation Updater Skill

You are helping update CLAUDE.md documentation based on doc-guard suggestions.

## When to Use

Automatically activate when the user:
- Requests documentation updates ("update docs", "fix documentation")
- Mentions doc-guard ("address doc-guard suggestions", "check pending docs")
- Wants to update CLAUDE.md ("update CLAUDE.md", "add to docs")
- Asks about pending documentation work

## Workflow

### Step 1: Check Pending Suggestions

First, check for pending documentation suggestions:

```bash
./hooks/cli/doc_guard_cli.py pending
```

**If no suggestions:**
- Ask the user what documentation they want to update
- Suggest checking recent code changes for undocumented patterns

**If suggestions exist:**
- Review each suggestion's summary and reason
- Note which files and sections need updates

### Step 2: Review Each Suggestion

For each suggestion in pending.json:

1. **Read the suggested file** (usually `CLAUDE.md` or `hooks/CLAUDE.md`)
2. **Locate the suggested section** (e.g., "Common Commands", "Key Patterns")
3. **Understand the reason** for the update
4. **Verify the suggested content** aligns with actual implementation

### Step 3: Follow Anchor Comment Conventions

When updating CLAUDE.md, follow these conventions:

**For Major Patterns:**

Add anchor comments for reusable, significant patterns:

```markdown
<!-- PATTERN-NAME -->
### Pattern Title

**Purpose**: Brief description of what this pattern does

**Usage**: When to use this pattern

**Implementation**:
- Key implementation details
- File references with line numbers

**Example**:
```language
# Code example
```

**See**: Related patterns or files
```

**For Command Reference:**

Update Common Commands section with executable examples:

```markdown
## Common Commands

```bash
# Command description
command-name --arg value

# Example use case
actual-example-command
```
```

**For Project Rules:**

Add to Project-Specific Rules with numbered list:

```markdown
## Project-Specific Rules

1. **Rule description** - Implementation requirement
2. **Next rule** - Rationale and consequences
```

### Step 4: Reference Anchors in Code

When a pattern has an anchor comment, reference it in related code:

```python
"""Module implementing X.

Implements <!-- PATTERN-NAME --> from CLAUDE.md:section.
See CLAUDE.md for usage and examples.
"""
```

This creates bidirectional discoverability:
- Documentation → Code: References show where pattern is used
- Code → Documentation: Docstrings point to detailed guidance

### Step 5: Verify Updates

After updating documentation:

1. **Validate markdown** - Ensure proper formatting
2. **Check anchor references** - Verify they point to correct sections
3. **Test commands** - Run any command examples added
4. **Review consistency** - Ensure style matches existing docs

### Step 6: Clear Suggestions

After addressing all suggestions:

```bash
./hooks/cli/doc_guard_cli.py clear
```

This removes the pending.json file and marks suggestions as resolved.

## Common Updates

### Adding a New Pattern

When documenting a reusable pattern:

1. **Choose anchor name**: Use UPPERCASE-WITH-HYPHENS
   - Good: `BACKGROUND-WORKERS`, `METADATA-SIDECAR`
   - Bad: `background_workers`, `MetadataSidecar`

2. **Add anchor before section**:
   ```markdown
   <!-- NEW-PATTERN -->
   ### Pattern Title
   ```

3. **Include these subsections**:
   - **Purpose**: What problem does it solve?
   - **Usage**: When to use it?
   - **Implementation**: Key technical details
   - **Example**: Working code snippet
   - **See**: Related patterns or files

4. **Reference in code**:
   ```python
   """Implements <!-- NEW-PATTERN --> from CLAUDE.md."""
   ```

### Updating Command Reference

When adding new commands:

1. **Find Common Commands section**
2. **Add command with context**:
   ```markdown
   # Description of what command does
   command-name --arg value

   # Specific use case example
   real-example-with-actual-values
   ```

3. **Group related commands** together
4. **Include output examples** if helpful

### Adding Project Rules

When documenting project requirements:

1. **Find Project-Specific Rules section**
2. **Add as numbered item**:
   ```markdown
   N. **Rule title** - Brief requirement description
   ```

3. **Include rationale** if not obvious
4. **Reference related patterns** with anchor comments

### Updating Hook Documentation

When documenting hooks:

1. **Update Hook Types Reference table**:
   ```markdown
   | Hook | Trigger | Purpose | File |
   |------|---------|---------|------|
   | HookName | When it runs | What it does | path/to/file.py |
   ```

2. **Add to Key Patterns** if pattern is reusable

3. **Update Common Gotchas** if there are known issues

## Best Practices

### Documentation Quality

- **Be specific**: Include file paths with line numbers
- **Show examples**: Working code snippets > abstract descriptions
- **Link concepts**: Cross-reference related patterns
- **Keep current**: Update docs when implementation changes

### Anchor Comments

- **Use sparingly**: Only for major, reusable patterns
- **Choose clear names**: Should describe the pattern clearly
- **Reference consistently**: Always use same anchor in related code
- **Maintain index**: Update anchor cross-reference if it exists

### Writing Style

- **Imperative mood**: "Run tests" not "You should run tests"
- **Concrete examples**: Show actual commands, not templates
- **Clear structure**: Use headings, tables, code blocks
- **Scannable**: Use bullets, tables, and formatting

## Integration with Doc-Guard

**Doc-guard workflow:**

1. **Hook detects changes** to documented areas (hooks/lib/\*.py, etc.)
2. **Generates suggestions** in pending.json
3. **This skill guides updates** based on suggestions
4. **User clears suggestions** after addressing

**Pending.json structure:**

```json
{
  "entries": [
    {
      "summary": "Brief description of change",
      "suggestions": [
        {
          "file": "CLAUDE.md",
          "section": "Key Patterns",
          "reason": "New pattern added",
          "suggested_content": "Content to add"
        }
      ]
    }
  ]
}
```

## Tips

### Finding the Right Section

Common CLAUDE.md sections and when to use them:

| Section | When to Update |
|---------|----------------|
| Tech Stack | New dependencies, framework changes |
| Project Structure | New directories, file organization changes |
| Common Commands | New CLI commands, common operations |
| Key Patterns | Reusable architectural patterns |
| Project-Specific Rules | New requirements, conventions |
| Hook Types Reference | New hooks, hook changes |
| Testing Requirements | New test patterns, coverage changes |

### Handling Unclear Suggestions

If a doc-guard suggestion is unclear:

1. **Read the triggering code** to understand what changed
2. **Search for similar patterns** in existing docs
3. **Ask the user** what aspects need documentation
4. **Start with basics** and iterate based on feedback

### Maintaining Consistency

When updating docs:

- **Match existing style**: Follow format of similar sections
- **Use consistent terminology**: Check existing usage
- **Preserve structure**: Keep established section organization
- **Update related sections**: Keep cross-references accurate

## Example Workflows

### Example 1: New Pattern Added

**Situation**: Code added new background worker pattern, doc-guard suggests update

```bash
$ ./hooks/cli/doc_guard_cli.py pending
📋 1 pending suggestion(s):

[1] New background worker for analytics
    → CLAUDE.md: Key Patterns
      Reason: New fire-and-forget pattern in analytics_worker.py
```

**Actions:**
1. Read `analytics_worker.py` to understand pattern
2. Check if similar to existing `BACKGROUND-WORKERS` pattern
3. Either extend existing pattern or create new anchor
4. Add example showing analytics-specific usage
5. Reference anchor in `analytics_worker.py` docstring
6. Clear suggestions

### Example 2: New Command Added

**Situation**: New CLI command added, needs documentation

```bash
$ ./hooks/cli/doc_guard_cli.py pending
📋 1 pending suggestion(s):

[1] New epic-verify command
    → CLAUDE.md: Common Commands
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

### Example 3: Hook Configuration Changed

**Situation**: New PreToolUse hook added

```bash
$ ./hooks/cli/doc_guard_cli.py pending
📋 1 pending suggestion(s):

[1] New websearch-to-exa validator hook
    → CLAUDE.md: Hook Configuration
      Reason: New PreToolUse hook enforces Exa usage
```

**Actions:**
1. Find "Hook Configuration" section
2. Update PreToolUse hooks table
3. Add to "Project-Specific Rules" if enforced
4. Document in "Common Gotchas" if there are issues
5. Clear suggestions

## References

- **Main documentation**: `~/formaltask/CLAUDE.md`
- **Hook documentation**: `~/formaltask/hooks/CLAUDE.md`
- **Doc-guard CLI**: `hooks/cli/doc_guard_cli.py`
- **Pending suggestions**: `.claude/doc-guard/pending.json`
- **Anchor conventions**: See main CLAUDE.md for examples
