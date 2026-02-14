---
name: mapping-elegant
description: Maps codebases at multiple abstraction levels and surfaces antirez-style
  elegance findings. Use when "map architecture", "elegance audit", "show coupling",
  or "find over-engineering". For execution tracing, use tracing-code-flows instead.
uses_skill_run: true
spawns_subagents: true
required_todos:
- mode-selection
- spawn-global-mappers
- spawn-global-verifiers
- spawn-module-investigators-deep-only
- spawn-module-verifiers-deep-only
- synthesis
---

<role>
WHO: Architecture surgeon
ATTITUDE: Complexity is guilt. Find it. Name it. Cut it.
</role>

<purpose>
Your job is to produce layered codebase maps and surface antirez violations with file:line evidence.
</purpose>

## Phase 0: Mode Selection

| Trigger | Action |
|---------|--------|
| Default | Quick mode (L1 only). Skip AskUserQuestion |
| User requests depth | Ask: "What depth?" → Quick / Standard (Recommended) / Deep |

**Quick:** L1 system map only, no elegance audit
**Standard:** L1 + L2 + elegance findings
**Deep:** Standard + per-module deep dives for top hotspots

---

## Phase 1: Spawn Global Mappers (Parallel)

| Mode | Agents | Description |
|------|--------|-------------|
| Quick | Direct | Use auggie + warpgrep inline. Present L1 map. **STOP.** |
| Standard | 3 | l1-system-mapper + l2-module-mapper + elegance-hunter |
| Deep | 3 | Same as Standard |

**Prompts:** `references/global-mapper-prompts.md`

**ALL 3 spawns in ONE message:**
```python
Task(subagent_type="l1-system-mapper", run_in_background=True, prompt=l1_prompt)
Task(subagent_type="l2-module-mapper", run_in_background=True, prompt=l2_prompt)
Task(subagent_type="elegance-hunter", run_in_background=True, prompt=elegance_prompt)
```

**Output files:** `{outputs}/01-l1-system.md`, `01-l2-modules.md`, `01-elegance.md`

---

## Phase 2: Spawn Global Verifiers (Parallel)

**BLOCKING:** Phase 1 outputs exist.

| Mode | Agents |
|------|--------|
| Quick | Skip |
| Standard/Deep | 3 verifiers (one per mapper) |

**Prompts:** `references/global-mapper-prompts.md` (verifier section)

**ALL 3 spawns in ONE message:**
```python
Task(subagent_type="mapping-verifier", prompt=l1_verifier_prompt)
Task(subagent_type="mapping-verifier", prompt=l2_verifier_prompt)
Task(subagent_type="mapping-verifier", prompt=elegance_verifier_prompt)
```

**Output files:** `{outputs}/02-*-verified.md`

---

## Phase 3: Intermediate Synthesis

**BLOCKING:** Phase 2 outputs exist.

| Mode | Action |
|------|--------|
| Quick | Present L1 inline. **STOP here.** |
| Standard | Write `synthesis-global.md`. Copy to `synthesis.md`. **STOP.** |
| Deep | Write `synthesis-global.md`. Continue to Phase 4. |

**Template:** `references/synthesis-templates.md` (Intermediate section)

Key content:
- Modules ranked by `external_importers × file_count`
- Cross-module coupling matrix
- Global elegance findings

---

## Phase 4: Spawn Module Investigators (Deep Only)

**BLOCKING:** Mode is Deep. Phase 3 complete.

Select top 3-5 hotspot modules from synthesis ranking.

**Prompts:** `references/module-investigator-prompts.md`

**ALL module investigators in ONE message:**
```python
for module in hotspot_modules:
    Task(subagent_type="module-deep-investigator", prompt=investigator_prompt)
```

**Output files:** `{outputs}/04-module-{name}.md`

---

## Phase 5: Spawn Module Verifiers (Deep Only)

**BLOCKING:** Phase 4 outputs exist.

**ALL module verifiers in ONE message:**
```python
for module in hotspot_modules:
    Task(subagent_type="module-investigator-verifier", prompt=verifier_prompt)
```

**Output files:** `{outputs}/05-module-{name}-verified.md`

---

## Phase 6: Final Synthesis (Deep Only)

**BLOCKING:** Phase 5 outputs exist.

**Template:** `references/synthesis-templates.md` (Final section)

Combine:
- Global synthesis
- Per-module verified findings
- Verification summary table
- Action items + Onboarding trail

Write to `{run_dir}/synthesis.md`.

---

## Output Files Summary

| Phase | Quick | Standard | Deep |
|-------|-------|----------|------|
| 1 | inline | `01-*.md` (3) | `01-*.md` (3) |
| 2 | skip | `02-*-verified.md` (3) | `02-*-verified.md` (3) |
| 3 | inline | `synthesis.md` | `synthesis-global.md` |
| 4 | skip | skip | `04-module-*.md` (N) |
| 5 | skip | skip | `05-module-*-verified.md` (N) |
| 6 | skip | skip | `synthesis.md` |

---

<rules>
- auggie for semantic discovery, warpgrep for tracing, Grep for counts
- Every finding needs file:line or it's speculation
- Coupling matrix uses actual import counts, not estimates
- Module investigators MUST read synthesis first
- Module verifiers hunt for MISSED violations
- **ALL spawns in ONE message** for true parallel execution
- Only confirmed findings make final synthesis
</rules>
