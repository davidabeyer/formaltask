---
consumes: []
produces: [oss-target]
---

## Discovery

Locate the package and establish audit scope.

```python
Glob(pattern="*/__init__.py")
Glob(pattern="src/*/__init__.py")
Read("pyproject.toml")
Glob(pattern="README*")
```

Clarify with user:
- Which package to audit
- Target audience (library, CLI, API)
- Exemplar projects to compare against

**quick:** Quick discovery, note obvious gaps. Identify package and move on.

**full:** Complete discovery. Read all entry points, map package boundaries.

**EXIT CRITERIA:** Package identified, audience known, exemplars chosen.
