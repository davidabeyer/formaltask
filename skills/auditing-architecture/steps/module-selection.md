---
consumes: [architecture-map]
produces: [selected-modules]
optional: true
---
# Phase 2: Module Selection (full only)

**quick:** Skip this phase. Go directly to Phase 1-Single.

**full:** Based on architecture handoff, select 2-4 modules.

Use branching to evaluate module selection:

```xml
<branching>
  <fork point="Which modules address the REAL CONCERN from meta-analysis?"/>
  <path id="core" name="Core business logic">
    [Highest value, most critical to get right. Which modules are load-bearing?]
  </path>
  <path id="churn" name="Frequently modified">
    [Check `git log --oneline --since='3 months ago'`. High churn = high risk.]
  </path>
  <path id="concern" name="User-specified concerns">
    [What did they mention? These modules answer THEIR question, not mine.]
  </path>
  <path id="integration" name="Integration points">
    [Boundaries between modules. Where do most bugs hide?]
  </path>
  <converge when="Selected 2-4 modules that address real concern with evidence"/>
</branching>
```

Write selection rationale to `{run_dir}/outputs/02-module-selection.md`.
