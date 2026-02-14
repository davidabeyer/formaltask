---
consumes: [audit-mode]
produces: [audit-findings]
optional: true
---
# Phase 1-Single: Direct Audit (Single Module Mode)

**quick:** This is the default path. Execute directly.

**full:** If user selected "Single module" in Phase 0:

1. Ask for module path or let user pick from codebase structure
2. Read EVERY file in module - no skimming
3. Trace 3-5 execution paths through the module
4. Apply 6 quality criteria from `references/deep-analysis-framework.md`:
   - Simplicity: Does each function do one thing?
   - Clarity: Can I understand each function in 2 minutes?
   - Data Visibility: Can I see what data exists and its state?
   - Necessity: Does each abstraction earn its existence?
   - Test Honesty: Do tests actually test what they claim?
   - Liveness: Is all code reachable?
5. Produce findings directly (no workers)

For each finding: file:line, code quote (5+ lines), problem, impact, fix.

Skip Phases 1-5 entirely. Write directly to `synthesis.md`.
