# Common Objections and Warning Signs

## Addressing Objections

**"I'll test after implementation"**
Tests written after code passes immediately, proving nothing about validity. The test becomes a rubber stamp rather than a specification.

**"This is too simple to test"**
Simplicity makes testing easier, not less necessary. Simple code still needs verification. Bugs often hide in "simple" code.

**"Manual testing is sufficient"**
Manual testing is not reproducible, systematic, or automated. Regression detection requires automation. Manual testing doesn't scale.

**"Just this once, I'll skip the test"**
Exceptions become habits. tdd-guard blocks this rationalization with technical enforcement. One skip becomes ten.

**"I need to prototype first"**
Write test describing desired interface, then prototype implementation. Test guides design. Delete prototype after understanding the problem.

**"Tests slow me down"**
Tests slow you down now but save debugging time later. The debugging time saved exceeds the test-writing time. Compounding returns.

**"The requirements keep changing"**
Tests document current requirements. When requirements change, update tests first. Tests become living documentation of expected behavior.

## Warning Signs

TDD methodology is failing when:

| Warning Sign | Impact |
|--------------|--------|
| Writing code before tests | Tests prove nothing, miss edge cases |
| Rationalizing "just this once" exceptions | Habit formation, discipline erosion |
| Assuming manual testing eliminates need | Regression bugs, inconsistent quality |
| Tests passing immediately (no RED phase) | Tests validate nothing |
| tdd-guard frequently disabled (>1x/week) | Process breakdown |
| Large commits mixing tests and implementation | Lost traceability |

## Recovery Steps

When you've violated TDD:

1. **Delete** implementation code written without tests
2. **Write** failing test describing desired behavior
3. **Verify** test actually fails
4. **Write** minimal implementation
5. **Commit** test + implementation together

## Self-Assessment Checklist

Ask yourself:

- [ ] Did I write the test before the implementation?
- [ ] Did I see the test fail with the expected error?
- [ ] Did I write only enough code to pass this test?
- [ ] Did I run the full test suite before committing?
- [ ] Would deleting my implementation cause the test to fail?

If any answer is "no", you're not doing TDD.
