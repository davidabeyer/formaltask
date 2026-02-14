# Exhaustive Reading Prompt

Phase 1: Build the code index that all subsequent passes will use.

---

## THE PROMPT

```
PHASE 1: EXHAUSTIVE CODE READING

TARGET: {target}
WORKING DIR: {working_dir}

You are building the foundation for a deep audit. Your job is to read
EVERY LINE of code and produce a CODE INDEX that subsequent passes will use.

This is NOT a summary. This is an annotated code repository.

---

CRITICAL RULES:

1. READ COMPLETELY. No skimming. No "and so on." Every function, every class.

2. OUTPUT ACTUAL CODE. Not descriptions. Not "handles X."
   BAD: "create_session handles session creation"
   GOOD: ```python
         def create_session(config):
             if not config.project_root:
                 raise ValueError("project_root required")
             ...actual code...
         ```

3. ANNOTATE WITH OBSERVATIONS. What you notice. Questions for later passes.
   - "Single responsibility or mixed concerns?"
   - "Where does this data come from?"
   - "Who calls this?"

4. NO CRITICISM YET. Pure observation. Judgment comes in later passes.

---

RESEARCH PROTOCOL:

1. LIST ALL FILES
   Glob(pattern="**/*.py", path="{target}")
   (Adjust pattern for language)

2. FOR EACH FILE, READ COMPLETELY
   Read(file_path) - the entire file, not first 50 lines

3. FOR EACH FUNCTION/CLASS:
   - Extract the complete code
   - Note line numbers (start-end)
   - Add observations (not judgments)

4. BUILD CALL GRAPH
   - What calls what?
   - Entry points (CLI, API, tests)
   - Dead ends (nothing calls this?)

5. NOTE QUESTIONS
   - Things unclear from code alone
   - Things to investigate in passes

---

OUTPUT: {working_dir}/01-code-index.md

FORMAT:

```markdown
# Code Index: {target}

Generated: {timestamp}
Files: {count}
Functions: {count}
Classes: {count}

## Overview

{2-3 sentences: what this module does, entry points, key abstractions}

## Call Graph

```
entry_point_1()
  → helper_a()
    → helper_b()
  → helper_c()

entry_point_2()
  → helper_a()  # shared
  → helper_d()
```

---

## File: {path/to/file.py}

### Imports
```python
{actual imports}
```
**External deps:** {list}
**Internal deps:** {list}

### Class: ClassName (lines X-Y)

```python
class ClassName:
    """Docstring if present."""

    def __init__(self, ...):
        {actual code}

    def method_one(self, ...):
        {actual code}
```

**Observations:**
- {observation 1}
- {observation 2}

**Questions:**
- {question for later passes}

### Function: function_name (lines X-Y)

```python
def function_name(args):
    """Docstring if present."""
    {actual code - complete, not truncated}
```

**Observations:**
- {observation 1}

**Callers:** {list of functions that call this, or "entry point" or "unknown"}
**Calls:** {list of functions this calls}

---

## File: {next file}
...

---

## Questions for Passes

### For Structure Pass
- {question about module boundaries}
- {question about call chains}

### For Data Pass
- {question about state ownership}
- {question about data flow}

### For Complexity Pass
- {question about mixed concerns}
- {question about unclear code}

### For Craft Pass
- {question about potential dead code}
- {question about unnecessary abstraction}
```

---

QUALITY GATE:

Before finishing, verify:
- [ ] Every file in {target} is indexed
- [ ] Every function has actual code, not description
- [ ] Line numbers are accurate
- [ ] Observations are present (not empty)
- [ ] Questions are specific (not generic)

If any check fails, go back and complete.
```

---

## Common Failures

| Failure | Symptom | Fix |
|---------|---------|-----|
| Summary instead of code | "handles session lifecycle" | Re-read, paste actual code |
| Truncation | "...and more..." | Read full file, include all |
| Missing files | File count doesn't match Glob | Re-run Glob, read missing |
| No observations | Empty observation sections | Actually think about the code |
| Generic questions | "Is this good?" | Be specific: "Who owns this state?" |
