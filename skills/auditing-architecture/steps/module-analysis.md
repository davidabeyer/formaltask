---
consumes: [selected-modules, architecture-map]
produces: [module-findings]
optional: true
---
# Phase 3: Deep Module Analysis (full only)

**quick:** Skip this phase. Go directly to Phase 1-Single.

**full:** Sequential module analysis. Each module gets full attention.

Track cross-module patterns with sequential reasoning:

```xml
<sequential>
  <thought id="M1">[Finding from module 1—e.g., "error handling inconsistent in db/"]</thought>
  <thought id="M2" builds="M1">[Same pattern in module 2? Or contradicts? "workers/ has same issue—systemic"]</thought>
  <revision revises="M1" reason="[if module 2 shows module 1 finding was wrong]">[Updated understanding]</revision>
</sequential>
```

```python
for module in selected_modules:
    Task(
        subagent_type="code-quality-auditor",
        description=f"Analyze {module['name']}",
        prompt=f"""## TARGET
{module['path']}

## OUTPUT
{run_dir}/outputs/03-module-{module['name']}-analysis.md

## TASK
DEEP MODULE ANALYSIS

**Context from architecture mapping:**
{architecture_summary}

Audit this module for:
- Simplicity: Does each function do one thing?
- Clarity: Can I understand each function in 2 minutes?
- Data Visibility: Can I see what data exists and its state?
- Necessity: Does each abstraction earn its existence?
- Test Honesty: Do tests actually test what they claim?
- Liveness: Is all code reachable?

For each finding: file:line, code quote (5+ lines), problem, impact, fix.
See references/deep-analysis-framework.md for quality criteria."""
    )
    # Wait before next module
```
