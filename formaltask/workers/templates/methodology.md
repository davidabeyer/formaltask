<methodology>
## Task Decomposition (Before Writing Code)

**FIRST**: Use TodoWrite to decompose this task into actionable items:
- Map each acceptance criterion to one or more todos
- Break complex steps into smaller, testable units
- Make todos specific and measurable
- Mark first todo as `in_progress` before starting work

**Progress Tracking Rules:**
- Mark todos completed immediately after each item (don't batch)
- Only one todo should be `in_progress` at any time
- Add new todos if you discover additional work during implementation

## TDD Workflow (Non-Negotiable)

**Red-Green-Refactor Cycle:**
1. **RED** - Write a failing test first, verify it actually fails
2. **GREEN** - Write minimal code to make the test pass
3. **REFACTOR** - Improve code quality while keeping tests green

**Rules:**
- NEVER write implementation before a test exists for that behavior
- ALWAYS verify test fails with expected error before implementing
- Write minimal code to pass the current test (no over-engineering)
</methodology>
