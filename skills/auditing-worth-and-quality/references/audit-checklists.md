# Antirez Audit Checklists

## File Existence Check

| Question | Action |
|----------|--------|
| Could this be 50 lines in an existing module? | Inline it |
| Is this a "completion wrapper" around core logic? | Move core, delete wrapper |
| Does it exist because "that's how we structure things"? | Challenge the structure |

## The Praise Test

> **Would antirez look at this code and PRAISE it?**

| If antirez would say... | Action |
|------------------------|--------|
| "Why does this exist?" | DELETE |
| "This is overbuilt" | SIMPLIFY |
| "Just inline this" | INLINE |
| "Clean. I like it." | KEEP |

## Deletion Checklist

| Question | Action |
|----------|--------|
| Would this exist in a 500-line Redis implementation? | Delete if NO |
| Is this an abstract factory or "flexibility"? | Inline or delete |
| Is this a wrapper that adds nothing? | Inline into caller |
| Config option nobody uses? | Delete |

## Quality Smells

| Smell | Fix |
|-------|-----|
| Nested 3+ levels deep | Early returns, extract condition |
| Function >25 LOC | Split or inline parts |
| Magic method (`__getattr__`, `__call__`) | Make explicit |
| Dense one-liner comprehension | Multi-line or variable |
| Not using context manager | `with` statement |
| String path manipulation | `pathlib.Path` |
| Manual iteration | List/dict/set comp |
| `isinstance()` dispatch | Single type or protocol |
| Bare `except Exception:` | Specific exception |
| 30-second rule violation | Rewrite until junior can read |

## Verification Commands

```bash
# Function unused?
grep -r "function_name(" formaltask --include="*.py" | grep -v "def function_name"

# Cross-module usage?
grep -r "from formaltask.{module}" formaltask --include="*.py"
```

**Use Grep tool** - Bash chokes on `\(`.

## Beautiful Alternatives

| Current State | Beautiful Alternative |
|---------------|----------------------|
| Two similar functions | Single function with parameter |
| Wrapper that just calls inner | Delete wrapper, expose inner |
| Config/flags nobody uses | Hardcode the one value used |
| Complex conditional | Simple early return |

**Nuclear question:** "If I deleted this entire file, what would break?"
- "nothing" → DELETE THE FILE
- "one function" → INLINE that function, delete file
