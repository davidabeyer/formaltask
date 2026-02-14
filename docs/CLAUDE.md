# docs/ CLAUDE.md

Documentation for the FormalTask project. Loaded when editing any file in `docs/`.

## Boundary Rule

**If removing it wouldn't change Claude's behavior, it belongs here in `docs/`, not in a CLAUDE.md.**

- CLAUDE.md files = operational constraints (commands, gotchas, patterns)
- docs/ = understanding (architecture, data flow, reference)
- Never duplicate between the two. CLAUDE.md can reference docs/ — never re-explain.

## Writing Rules

**Every sentence earns its place.** If it doesn't teach something, delete it.

- Imperative voice. "Use X" not "X can be used" or "You might want to use X."
- One idea per sentence. No compound explanations.
- Code examples over prose. Show, don't describe.
- Tables for structured data. Never a bulleted list of key-value pairs.
- ASCII diagrams for data flow. Never describe flow in prose when a diagram works.
- Headings are `##` section, `###` subsection. Never skip levels.
- File references use backtick paths: `formaltask/core/rules.py`. Never bare text.
- No hedge words: "might", "could", "perhaps", "generally", "typically."
- No meta-commentary: "In this section we will...", "As mentioned above..."
- No version history inside docs. That's what git is for.

## Structure Rules

| Directory | Content | Style |
| --- | --- | --- |
| `getting-started/` | Onboarding: install, first run | Step-by-step with bash blocks |
| `cli/` | Command reference | One file per noun. Table of arguments per verb. |
| `architecture/` | System design | Problem/architecture/details/files pattern (match `skill-spans.md`) |

## Architecture Doc Template

Every `architecture/*.md` follows this skeleton:

```
# Feature Name
One-line description.

## The problem
Why this exists. 2-3 sentences max.

## Data flow / Architecture
ASCII diagram showing the flow.

## Module map
Table: file | role

## [Detail sections as needed]
Specific to the feature.

## Files
Reference table of all relevant paths.
```

## CLI Doc Template

Every `cli/*.md` follows this skeleton:

```
# ft <noun>
One-line description.

## <noun> <verb>
```bash
ft <noun> <verb> [options]
```

### Arguments
Table: argument | description | default
```

## Anti-Patterns

- Explaining what code does line-by-line. Link to the file instead.
- Documenting internal implementation details that change frequently.
- Adding a doc for a feature that has no tests. Tests first.
- Creating a doc "just in case." Every doc must answer a question someone has asked.
- Mentioning dates, sprint names, or task IDs in docs. They rot instantly.

## When to Update Docs

Update docs in the SAME commit as the code change when:
- A CLI command is added, renamed, or gets new flags
- A module is created, moved, or deleted
- A data flow changes (new hook, new pipeline stage)
- An architecture doc's diagram no longer matches reality

Do NOT create a doc for:
- Internal refactors that don't change behavior
- Test-only changes
- Bug fixes to existing documented features
