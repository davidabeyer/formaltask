---
consumes: [agent-outputs]
produces: [collected-findings]
optional: false
---
# Collect Agent Outputs

Gather all agent outputs from the SkillRun outputs directory:

```python
from pathlib import Path
outputs = {}
for f in Path(outputs_dir).glob("*.md"):
    outputs[f.stem] = f.read_text()
```

Merge into a single findings document. Flag any agents that produced empty or error outputs.