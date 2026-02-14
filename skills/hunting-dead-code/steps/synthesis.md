---
consumes: [verified-findings, code-topology]
produces: [synthesis-report]
---

# Phase 4: Synthesis & Verdict

**quick:** Report findings directly with Kill/Suspect/Keep categories. No synthesis file needed.

**full:** Write synthesis to run directory:

```python
run.write_log("Starting synthesis", phase="Phase 4")

Task(subagent_type="findings-synthesis",
     prompt=f"Topology: {run.run_dir}/01-code-topology.md\nVerified findings: {run.run_dir}/03-verified-findings.md\nWrite to: {run.run_dir}/synthesis.md")
```
