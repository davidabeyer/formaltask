# Lens Prompts

Exact prompts for Phase 2 - one subagent per lens, reporting ALL findings.

---

## Common Preamble

```
PHASE 2: EXHAUSTIVE ANALYSIS - {LENS} LENS

COMPREHENSION: Read {working_dir}/01-comprehension.md FIRST
OUTPUT: Write to {working_dir}/02-{lens}.json

REPORT ALL FINDINGS. No limits. Group by severity.

This is an exhaustive audit. Every non-idiomatic pattern matters.
Style debt compounds - complete inventory enables batch fixes.

RESPECT INTENTIONS: If comprehension doc notes intentional deviations, skip those.

SEVERITY:
- P0: Causes bugs or misunderstandings NOW
- P1: Maintenance pain as code grows
- P2: Reduces readability but functional
- P3: Style preference, nice-to-have

TOOLS:
- mcp__auggie-mcp__codebase-retrieval
- mcp__morph-mcp__warpgrep_codebase_search
- Grep for patterns
- Read for full inspection
```

---

## Lens: Naming

```
{PREAMBLE}

LENS: NAMING
QUESTION: Where do names violate conventions or reduce clarity?

DETECTION:

1. CONVENTION VIOLATIONS
   Grep(pattern="def [A-Z]") - PascalCase functions (should be snake_case)
   Grep(pattern="class [a-z]") - lowercase classes (should be PascalCase)
   Grep(pattern="^[A-Z][a-z_]+ = ") - constants not UPPER_CASE

2. UNCLEAR NAMES
   Grep(pattern="def [a-z]\\(") - single-letter function names
   Grep(pattern="for [a-z] in") - single-letter loop variables (except i,j,k,x,y,z in math)
   Grep(pattern="[a-z] = ") in function bodies - single-letter assignments

3. BOOLEAN NAMING
   Search for boolean variables/parameters missing is_, has_, can_, should_ prefix
   Grep(pattern="def.*\\(.*: bool") - check parameter names

4. INCONSISTENT TERMINOLOGY
   Same concept with different names across files
   e.g., "user" vs "account" vs "profile" for same entity

5. ABBREVIATION OVERUSE
   Grep(pattern="def.*(_cb|_fn|_val|_str|_num|_arr|_lst|_dict|_obj)\\(")
   Unclear abbreviations: cfg, ctx, mgr, util, misc, tmp, ret, res

SEVERITY GUIDE:
- P0: Name actively misleads (e.g., `is_valid` returns non-boolean)
- P1: Inconsistent naming across related functions
- P2: Single-letter names in non-trivial contexts
- P3: Abbreviations that are understandable but not ideal

OUTPUT:
```json
{
  "lens": "naming",
  "findings": {
    "P0": [
      {
        "issue": "Misleading name",
        "file": "...",
        "line": N,
        "code": "...",
        "problem": "...",
        "suggestion": "..."
      }
    ],
    "P1": [...],
    "P2": [...],
    "P3": [...]
  },
  "total_count": N,
  "files_affected": N,
  "summary": "X naming issues across Y files"
}
```
```

---

## Lens: Typing

```
{PREAMBLE}

LENS: TYPING
QUESTION: Where are type hints missing, incorrect, or outdated?

DETECTION:

1. MISSING RETURN TYPES
   Grep(pattern="def [a-z_]+\\([^)]*\\):$") - functions without -> annotation
   Grep(pattern="def [a-z_]+\\([^)]*\\) ->") - check if present

2. MISSING PARAMETER TYPES
   Grep(pattern="def.*\\([a-z_]+,") - params without type hints
   Look for mixed typed/untyped parameters

3. ANY OVERUSE
   Grep(pattern=": Any") - count and check if specific type is knowable
   Grep(pattern="-> Any") - especially problematic for returns

4. OLD-STYLE TYPING (Python 3.9+ codebases)
   Grep(pattern="List\\[|Dict\\[|Set\\[|Tuple\\[|Optional\\[")
   Should be: list[...], dict[...], set[...], tuple[...], X | None
   Grep(pattern="Union\\[.*None\\]") - should be X | None

5. MISSING GENERIC CONSTRAINTS
   Classes using generics without proper TypeVar bounds
   Grep(pattern="class.*\\[T\\]") then check T definition

6. TYPED DICT VS DATACLASS
   Grep(pattern="TypedDict") - check if dataclass would be cleaner
   Look for dicts with fixed schemas that could be dataclasses

SEVERITY GUIDE:
- P0: Wrong type hint (annotated str, actually returns int)
- P1: Public API missing return types
- P2: Internal functions missing types
- P3: Old-style typing that works fine

RESPECT PYTHON VERSION:
Check comprehension doc for Python version. Don't flag `List[X]` as outdated
if targeting Python 3.8.

OUTPUT:
```json
{
  "lens": "typing",
  "findings": {
    "P0": [...],
    "P1": [...],
    "P2": [...],
    "P3": [...]
  },
  "total_count": N,
  "files_affected": N,
  "coverage_estimate": "X% of functions have return types",
  "summary": "..."
}
```
```

---

## Lens: Pythonic

```
{PREAMBLE}

LENS: PYTHONIC
QUESTION: Where are non-idiomatic patterns used instead of Pythonic alternatives?

DETECTION:

1. LOOP PATTERNS
   Grep(pattern="for .* in range\\(len\\(") - use enumerate()
   Grep(pattern="for i in range.*:\\s*\\n.*\\[i\\]") - indexed access in loop
   Grep(pattern="i = 0.*while.*i \\+= 1") - manual counter

2. DICT PATTERNS
   Grep(pattern="if .* in .*:\n.*\\[") followed by else - use dict.get()
   Grep(pattern="try:.*\\[.*\\].*except KeyError") - use dict.get()
   Grep(pattern="\\.keys\\(\\)") - often unnecessary

3. CONTEXT MANAGERS
   Grep(pattern="= open\\(") without `with` - resource leak risk
   Grep(pattern="try:.*finally:.*\\.close\\(\\)") - use context manager

4. TRUTHINESS
   Grep(pattern="== True|== False") - use bare condition
   Grep(pattern="== None|!= None") - use `is None` / `is not None`
   Grep(pattern="len\\(.*\\) == 0|len\\(.*\\) > 0") - use truthiness

5. COMPREHENSIONS
   For loops that build lists/dicts/sets - could be comprehensions
   Grep(pattern="= \\[\\].*for.*\\.append\\(") - list building pattern

6. UNPACKING
   Grep(pattern="\\[0\\].*\\[1\\].*\\[2\\]") - indexed tuple access
   Grep(pattern="\\.split\\(\\)\\[0\\]") - could unpack

7. WALRUS OPERATOR (Python 3.8+)
   Pattern: assign then immediately use in condition
   if (match := pattern.search(text)):

8. STRING BUILDING
   Grep(pattern="\\+= ['\"]|['\"] \\+ ") - string concatenation in loops
   Should use join() or list building

SEVERITY GUIDE:
- P0: Resource leak (open without with)
- P1: Incorrect None comparison (== None vs is None)
- P2: range(len()) patterns, unnecessary .keys()
- P3: Missing comprehension opportunities

OUTPUT:
```json
{
  "lens": "pythonic",
  "findings": {
    "P0": [...],
    "P1": [...],
    "P2": [...],
    "P3": [...]
  },
  "total_count": N,
  "files_affected": N,
  "summary": "..."
}
```
```

---

## Lens: Organization

```
{PREAMBLE}

LENS: ORGANIZATION
QUESTION: Where is import/module structure non-standard?

DETECTION:

1. IMPORT ORDER (PEP 8)
   Correct: stdlib → third-party → local, with blank lines between
   Grep(pattern="^import |^from ") - analyze order in each file

2. UNUSED IMPORTS
   Run conceptual analysis: import X but X never used
   Grep(pattern="^from .* import .*") then search for usage

3. STAR IMPORTS
   Grep(pattern="from .* import \\*") - namespace pollution

4. CIRCULAR IMPORT RISKS
   Look for: from . import X in multiple related modules
   TYPE_CHECKING blocks indicate existing circular import workarounds

5. PUBLIC/PRIVATE CONSISTENCY
   Functions without _ prefix used only internally
   _ prefixed functions used externally
   Grep(pattern="def _[a-z]") then check for external usage

6. MODULE DOCSTRINGS
   Check first lines of .py files for module-level docstrings
   Grep(pattern="^\"\"\"", path="*.py") at file start

7. __all__ DEFINITION
   Public modules should define __all__
   Grep(pattern="^__all__") - check presence in public modules

8. RELATIVE VS ABSOLUTE IMPORTS
   Inconsistent usage within package
   Grep(pattern="from \\. import|from \\.\\. import")

SEVERITY GUIDE:
- P0: Star imports in non-__init__ files
- P1: Circular import that causes runtime issues
- P2: Wrong import order, missing __all__
- P3: Missing module docstrings

OUTPUT:
```json
{
  "lens": "organization",
  "findings": {
    "P0": [...],
    "P1": [...],
    "P2": [...],
    "P3": [...]
  },
  "total_count": N,
  "files_affected": N,
  "summary": "..."
}
```
```

---

## Lens: Documentation

```
{PREAMBLE}

LENS: DOCUMENTATION
QUESTION: Where is documentation missing, stale, or low-quality?

DETECTION:

1. MISSING DOCSTRINGS
   Public functions (no _ prefix) without docstrings
   Classes without class-level docstrings
   Grep(pattern="def [a-z][a-z_]+\\(") then check next line for """

2. STALE COMMENTS
   Comments that don't match adjacent code
   TODO/FIXME comments older than 6 months (check git blame)
   Grep(pattern="# TODO|# FIXME|# HACK|# XXX")

3. OBVIOUS COMMENTS
   Grep(pattern="# increment|# loop|# return|# set .* to")
   Comments that just restate the code

4. MISSING PARAMETER DOCS
   Docstrings without Args/Parameters section
   Check docstring style from comprehension (Google vs NumPy vs Sphinx)

5. MISSING RETURN DOCS
   Functions with non-None returns but no Returns section

6. MISSING EXCEPTION DOCS
   Functions with `raise` but no Raises section
   Grep(pattern="raise [A-Z]") then check docstring

7. OUTDATED DOCSTRINGS
   Docstring mentions parameters that don't exist
   Docstring missing new parameters

SEVERITY GUIDE:
- P0: Docstring actively wrong (documents removed parameter)
- P1: Public API missing docstrings
- P2: Complex internal functions missing docs
- P3: Obvious comments, missing module docs

OUTPUT:
```json
{
  "lens": "documentation",
  "findings": {
    "P0": [...],
    "P1": [...],
    "P2": [...],
    "P3": [...]
  },
  "total_count": N,
  "files_affected": N,
  "docstring_coverage": "X% of public functions documented",
  "summary": "..."
}
```
```

---

## Lens: Modernization

```
{PREAMBLE}

LENS: MODERNIZATION
QUESTION: Where are old patterns used when modern alternatives exist?

DETECTION:

1. PATH HANDLING
   Grep(pattern="os\\.path\\.|os\\.getcwd|os\\.listdir|os\\.makedirs")
   Should use pathlib.Path in most cases

2. STRING FORMATTING
   Grep(pattern="% [sd]|% \\(|%s|%d") - old % formatting
   Grep(pattern="\\.format\\(") - .format() (f-strings usually cleaner)

3. FILE HANDLING
   Grep(pattern="open\\(.*\\)\\.read\\(\\)|open\\(.*\\)\\.write\\(")
   Without context manager

4. DICT/LIST CONSTRUCTORS
   Grep(pattern="dict\\(\\)|list\\(\\)|tuple\\(\\)") - use literals {}, [], ()
   Exception: dict() for keyword args dict(a=1, b=2)

5. DATACLASS OPPORTUNITIES
   Classes with only __init__ setting self.X = X pattern
   Grep(pattern="def __init__.*self\\.[a-z]+ = [a-z]+") - repeated pattern

6. NAMEDTUPLE OPPORTUNITIES
   Tuples with semantic meaning being indexed
   Return values that are tuples with consistent structure

7. EXCEPTION CHAINING
   Grep(pattern="except.*:\n.*raise") without `from`
   Should be `raise X from e` or `raise X from None`

8. SUBPROCESS PATTERNS
   Grep(pattern="os\\.system|os\\.popen")
   Should use subprocess module

9. ENUM OPPORTUNITIES
   Magic strings/numbers used as constants
   Grep(pattern='if .* == ["\'][a-z]+["\']') - string comparisons

SEVERITY GUIDE:
- P0: Security issue (os.system with user input)
- P1: os.path in new code, missing exception chaining
- P2: % formatting, dict() instead of {}
- P3: Minor modernization opportunities

RESPECT PYTHON VERSION:
Don't flag f-strings if targeting Python 3.5
Don't flag walrus operator if targeting < 3.8
Check comprehension doc for version constraints.

OUTPUT:
```json
{
  "lens": "modernization",
  "findings": {
    "P0": [...],
    "P1": [...],
    "P2": [...],
    "P3": [...]
  },
  "total_count": N,
  "files_affected": N,
  "summary": "..."
}
```
```
