---
consumes: [hunt-findings]
produces: [verified-findings]
optional: true
---

# Phase 3: Adversarial Verification (full only)

For each finding, attempt to disprove it.

```python
run.write_log("Starting adversarial verification", phase="Phase 3")

Task(subagent_type="adversarial-verifier",
     prompt=f"Hunter outputs: {run.outputs}/\nWrite to: {run.run_dir}/03-verified-findings.md")

run.write_log("Verification complete", phase="Phase 3")
```
