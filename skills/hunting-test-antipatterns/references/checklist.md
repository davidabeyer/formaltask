# Testing Anti-Patterns Checklist

## Before Writing Test

- [ ] Am I testing real behavior or mock behavior?
- [ ] Do I understand what I'm mocking and why?
- [ ] Is my mock complete (matches real API contract)?
- [ ] Am I adding test-only methods to production code?
- [ ] Am I writing the test BEFORE implementation?

## While Writing Test

- [ ] Minimal mocks (only external dependencies)
- [ ] Complete mocks (all fields, not just what I need now)
- [ ] Real assertions (behavior, not mock.called)
- [ ] Test utilities separate from production code
- [ ] Test fails first (RED phase verified)

## After Writing Test

- [ ] Test fails before implementation (proves it tests something)
- [ ] Test passes after implementation (proves code works)
- [ ] No test-only methods added to production classes
- [ ] Mocks justified and documented
- [ ] Factory functions for complex mocks

## Red Flags

- [ ] More mock setup than assertions - Too many mocks
- [ ] mock.assert_called() without behavior checks - Testing mocks
- [ ] Production cleanup() methods - Test-only pollution
- [ ] Incomplete mock dicts - Will break later
- [ ] "I'll test this later" - Deferred testing
