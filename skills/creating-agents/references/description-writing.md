# Description Writing (Critical for Invocation)

The `description` field determines when Claude invokes the agent. Follow this pattern:

## Pattern

```yaml
description: >
  MUST BE USED when [specific scenario requiring this agent].
  Use PROACTIVELY when [early trigger condition].
  Examples - "[user phrase 1]" → Launch to [action] |
  "[user phrase 2]" → Deploy to [action] |
  "[user phrase 3]" → Use for [action]
```

## Anti-Patterns

- "Does code review" (too vague, no trigger)
- "Helps with testing" (no specificity)
- "General purpose agent" (defeats specialization)

## Good Examples

- "MUST BE USED after writing/modifying code for comprehensive review"
- "MUST BE USED when encountering errors, test failures, or unexpected behavior"
- "MUST BE USED when completing FormalTask tasks to verify acceptance criteria"
