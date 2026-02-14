---
consumes: [oss-target]
produces: [api-index]
---

## API Inventory

Catalog every public symbol in the package.

**quick:** List public API yourself inline. Skip subagent.

**full:** Single opus agent reads EVERY public symbol.

```python
Task(
    subagent_type="general-purpose",
    model="opus",
    description=f"API inventory {TARGET}",
    prompt=f"""**Role:** Python API documentation specialist.

## TARGET
Package: {TARGET} at {PACKAGE_PATH}

## OUTPUT PATH
Write to: {outputs_dir}/01-api-index.md

## TASK
Inventory all public API:
- Every public class, function, type with actual signatures
- Exports (__all__)
- Line numbers for each symbol"""
)
```

**QUALITY GATE:** Must contain actual signatures, not descriptions.

**EXIT CRITERIA:** `01-api-index.md` exists with real code signatures.
