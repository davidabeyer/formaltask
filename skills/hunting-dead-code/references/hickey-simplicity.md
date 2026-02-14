# Rich Hickey on Simplicity

Core principles from the creator of Clojure, applied to dead code hunting.

---

## Simple vs Easy

**Simple**: Not compound, not complected, has one role
**Easy**: Near at hand, familiar, convenient

Dead code is neither simple nor easy - it adds complexity without adding capability.

---

## Key Principles for Dead Code

### "Simplicity is a prerequisite for reliability."

Dead code is unreliable documentation. It claims to do something but doesn't execute.
Every line you don't delete is a line someone might try to maintain.

### "Programmers know the benefits of everything and the tradeoffs of nothing."

The benefit of keeping dead code: "I might need it someday."
The tradeoff: confusion, maintenance burden, false confidence in test coverage.

### "Simplicity is not about you."

You might understand why that commented block exists. The next developer won't.
Delete it. Git remembers.

---

## The Complecting Problem

Dead code complects (braids together) the system in harmful ways:

| What it complects | How |
|-------------------|-----|
| Past and Present | Old implementation lives alongside new |
| Intent and Action | Code exists but doesn't execute |
| Coverage and Confidence | Tests might cover dead paths |
| Documentation and Reality | Comments describe deleted behavior |

---

## Hickey's Questions Applied

When evaluating suspected dead code, ask:

1. **What is it for?** If you can't answer clearly, it's dead.
2. **Is it simple?** Dead code adds complexity with zero benefit.
3. **Is it complected?** Dead code braids past mistakes into present code.
4. **Would you write this today?** If no, delete it.

---

## Quotes

> "I think that large amounts of complexity come from our tools, not from our problems."

Dead code is complexity from our past, not from our problems.

> "Simple is often erroneously mistaken for easy. 'Easy' means 'to be at hand', 'to be approachable'. 'Simple' is the opposite of 'complex' which means 'being intertwined', 'being tied together'. Simple != easy."

Deleting dead code isn't easy (it requires understanding), but it makes the system simpler.

> "A program that produces incorrect results twice as fast is infinitely slower."

A codebase with dead code doesn't produce incorrect results - but it produces incorrect understanding.

---

## Application to Hunting

When you find suspected dead code:

1. **Don't justify keeping it** - That's the path to complexity
2. **Don't fear deleting it** - Git is your safety net
3. **Do verify it's truly dead** - Dynamic usage patterns exist
4. **Do delete with confidence** - Simpler is better
