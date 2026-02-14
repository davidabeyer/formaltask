# Documentation Best Practices

## Documentation Quality

- **Be specific**: Include file paths with line numbers
- **Show examples**: Working code snippets > abstract descriptions
- **Link concepts**: Cross-reference related patterns
- **Keep current**: Update docs when implementation changes

## Writing Style

- **Imperative mood**: "Run tests" not "You should run tests"
- **Concrete examples**: Show actual commands, not templates
- **Clear structure**: Use headings, tables, code blocks
- **Scannable**: Use bullets, tables, and formatting

## Handling Unclear Suggestions

If a doc-guard suggestion is unclear:

1. **Read the triggering code** to understand what changed
2. **Search for similar patterns** in existing docs
3. **Ask the user** what aspects need documentation
4. **Start with basics** and iterate based on feedback

## Maintaining Consistency

When updating docs:

- **Match existing style**: Follow format of similar sections
- **Use consistent terminology**: Check existing usage
- **Preserve structure**: Keep established section organization
- **Update related sections**: Keep cross-references accurate

## Verification Steps

After updating documentation:

1. **Validate markdown** - Ensure proper formatting
2. **Check anchor references** - Verify they point to correct sections
3. **Test commands** - Run any command examples added
4. **Review consistency** - Ensure style matches existing docs
