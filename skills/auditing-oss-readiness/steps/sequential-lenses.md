---
consumes: [api-index]
produces: [lens-outputs]
optional: true
---

## Sequential Lenses (full only)

**quick:** Skip. Audit key areas yourself inline: API naming, README quality, test coverage, obvious security issues.

**full:** 6 custom agents, run SEQUENTIALLY (NOT parallel). Each builds on previous.

```python
LENSES = [
    "oss-lens-api-surface",       # Naming, consistency, completeness
    "oss-lens-documentation",     # README, docstrings, examples
    "oss-lens-test-surface",      # Public API test coverage
    "oss-lens-security-posture",  # Input validation, injection, secrets
    "oss-lens-configuration-ux",  # Defaults, env vars, discoverability
    "oss-lens-distribution-ready" # Packaging, versioning, changelog
]

for i, lens in enumerate(LENSES, 2):
    Task(
        subagent_type=lens,
        prompt=f"""## TARGET
Package: {TARGET} at {PACKAGE_PATH}
API Index: {outputs_dir}/01-api-index.md

## OUTPUT PATH
Write JSON to: {outputs_dir}/{i:02d}-{lens.replace('oss-lens-', '')}.json

## PREVIOUS OUTPUTS
{outputs_dir}/"""
    )
    # WAIT before next lens
```

**EXIT CRITERIA:** All 6 lens outputs exist.
