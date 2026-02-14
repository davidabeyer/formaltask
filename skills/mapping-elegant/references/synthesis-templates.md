# Synthesis Templates

## Intermediate Synthesis (Phase 3)

```markdown
# Global Synthesis: {project}

## Modules Ranked by Complexity

| Module | External Importers | Files | Violations | Deep Dive? |
|--------|-------------------|-------|------------|------------|
| db/ | 64 | 5 | 0 | YES |

## Cross-Module Coupling (Verified)
{Coupling matrix from L2 verified}

## Global Elegance Findings (Verified)
{Violations from elegance verified}
```

---

## Final Synthesis (Phase 6 - Deep Mode)

```markdown
# Architecture Map: {project}

**Date:** {date} | **Mode:** Deep
**Global:** 3 mappers + 3 verifiers | **Module:** N investigators + N verifiers

## At a Glance
- {N} entry points | {N} modules | {circular_deps}
- THE hotspot: {file} ({N} importers)
- {N} elegance violations

## System Overview (L1 Verified)
{From 02-l1-verified.md}

## Module Dependencies (L2 Verified)
{Coupling matrix from 02-l2-verified.md}

## Global Elegance (Verified)
{From 02-elegance-verified.md}

---

## Per-Module Deep Dives

### {module}/ (Verified)
**Context:** {inbound} modules depend → Depends on {outbound} modules

| Section | Content |
|---------|---------|
| L2 Internal | {From 05-module-{module}-verified.md} |
| L3 Components | {Mermaid diagram} |
| L4 Hotspots | Function / File:Line / External Callers |
| Elegance | {Violations or "Clean"} |

---

## Verification Summary

| Level | Agent | Confirmed | Rejected | Modified | Missed |
|-------|-------|-----------|----------|----------|--------|
| Global | L1/L2/Elegance | N | N | N | - |
| Module | per-module | N | N | N | N |

## Action Items
1. {Priority fix}

## Onboarding Trail
1. Start: {entry_point}
2. Core flow: {path}
3. Gotcha: {warning}
```
