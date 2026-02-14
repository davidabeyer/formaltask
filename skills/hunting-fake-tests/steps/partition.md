---
consumes: [test-manifest]
produces: [batch-assignments]
optional: true
---

**quick:** Skip partitioning. Audit inline in synthesize step.

**full:** Split tests into 2-10 batches:
- Module coherence: same directory stays together
- Size balance: roughly equal test counts
- Small codebase (<50 files): 2-3 batches
- Large codebase (>200 files): up to 10 batches

**EXIT CRITERIA:** Batch assignments documented
