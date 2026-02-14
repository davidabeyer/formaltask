# Common Documentation Updates

## Adding a New Pattern

1. **Choose anchor name**: Use UPPERCASE-WITH-HYPHENS
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
   """Implements <!-- NEW-PATTERN --> from README.md."""
   ```

## Updating Command Reference

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

## Adding Project Rules

1. **Find Project-Specific Rules section**
2. **Add as numbered item**:
   ```markdown
   N. **Rule title** - Brief requirement description
   ```
3. **Include rationale** if not obvious
4. **Reference related patterns** with anchor comments

## Updating Hook Documentation

1. **Update Hook Types Reference table**:
   ```markdown
   | Hook | Trigger | Purpose | File |
   |------|---------|---------|------|
   | HookName | When it runs | What it does | path/to/file.py |
   ```
2. **Add to Key Patterns** if pattern is reusable
3. **Update Common Gotchas** if there are known issues

## Finding the Right Section

| Section | When to Update |
|---------|----------------|
| Tech Stack | New dependencies, framework changes |
| Project Structure | New directories, file organization changes |
| Common Commands | New CLI commands, common operations |
| Key Patterns | Reusable architectural patterns |
| Project-Specific Rules | New requirements, conventions |
| Hook Types Reference | New hooks, hook changes |
| Testing Requirements | New test patterns, coverage changes |
