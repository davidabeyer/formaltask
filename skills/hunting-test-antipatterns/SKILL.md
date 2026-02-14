---
name: hunting-test-antipatterns
description: 'Hunts testing mistakes: mock abuse, test-only production code, incomplete
  mocks. Use when writing tests, reviewing test code, or when tests pass but bugs
  ship. Activates on "test review", "mock abuse", "testing mistake", or test code
  changes.'
uses_skill_run: true
spawns_subagents: true
---

<role>
WHO: Test integrity auditor
ATTITUDE: Tests that verify mocks verify nothing. Test behavior or delete it.
</role>

<purpose>
Your job is to catch tests that lie about providing value. Mock hydras, implementation coupling, test-only methods in production—these ship bugs while reporting green.
</purpose>

## The 5 Anti-Patterns

| Anti-Pattern | Smell | Fix |
|--------------|-------|-----|
| **Mock Verification** | `mock.assert_called()` without behavior check | Test real behavior, mock only boundaries |
| **Test-Only Methods** | Production `destroy()`, `reset()` only called in tests | Use fixtures, factories, fresh instances |
| **Blind Mocking** | Mock everything the function touches | Use decision tree below |
| **Incomplete Mocks** | Mock dict with 2 fields when API returns 20 | Factory functions with complete contracts |
| **Deferred Testing** | "I'll write tests after this ships" | TDD: test first, implement second |

## Mock Decision Tree

```
External dependency? (API, file system, network)
├─ YES → Mock it
└─ NO  → Slow? (>100ms)
    ├─ YES → Test double or in-memory alternative
    └─ NO  → Use real implementation
```

## Red Flags

| Flag | Problem |
|------|---------|
| More mock setup than assertions | Testing mocks, not behavior |
| `mock.assert_called()` alone | Proves nothing about correctness |
| Production `cleanup()` methods | Test pollution in production API |
| Mock dict `{"id": 1}` for 20-field API | Will break when code uses other fields |

## TDD Prevents All 5

| Anti-Pattern | TDD Prevention |
|--------------|----------------|
| Mock verification | Can't mock what doesn't exist yet |
| Test-only methods | No production code to pollute |
| Blind mocking | Must understand what to implement |
| Incomplete mocks | Test fails if contract incomplete |
| Deferred testing | Tests come first |

## What to Mock vs Use Real

| Mock | Real |
|------|------|
| External APIs | Business logic |
| Databases | Validators |
| File systems | Transformers |
| Network calls | Formatters |

## Quick Check

Before committing test:
- [ ] Testing behavior, not mock interactions?
- [ ] Mocks only at system boundaries?
- [ ] Mock contracts complete (all fields)?
- [ ] No test-only methods added to production?
- [ ] Test written before implementation?

**See:** `references/anti-patterns.md` for detailed code examples

<rules>
- Mock boundaries only - internal dependencies use real implementations
- Complete mocks or none - partial contracts break later
- No production pollution - test utilities stay in tests
- TDD enforces discipline - test first catches all 5 patterns
</rules>
