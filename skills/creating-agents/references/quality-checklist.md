# Quality Checklist

Before deploying an agent:

## Required Checks

- [ ] `name` is kebab-case and descriptive
- [ ] `description` explains WHEN to invoke with trigger examples
- [ ] `tools` list is minimal (typically <10 tools)
- [ ] `TodoWrite` included if multi-step workflow
- [ ] No `Task/Agent` unless orchestrator
- [ ] No duplicate YAML fields

## Body Structure Checks

- [ ] Body uses XML tags for structure
- [ ] `<workflow>` has clear, numbered steps
- [ ] `<output_format>` specifies exact format expected
- [ ] `<rules>` includes security constraints

## Validation

- [ ] Tested invocation works correctly

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| 50+ tools | Bloat, confusion, security risk | Restrict to essential tools |
| Vague description | Won't trigger correctly | Add specific scenarios and examples |
| No output format | Inconsistent results | Define exact structure |
| Missing rules | Unpredictable behavior | Add explicit constraints |
| Duplicate YAML | Parse errors | Review frontmatter carefully |
| `Task/Agent` in subagent | Recursive spawning risk | Remove unless orchestrator |
| Missing TodoWrite in complex agent | No progress visibility | Add for multi-step workflows |
