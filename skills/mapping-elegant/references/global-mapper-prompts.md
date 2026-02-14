# Global Mapper Task Prompts

## L1 System Mapper

```
## TARGET
{target_path}

## OUTPUT
Write to: {outputs}/01-l1-system.md

## DONE WHEN
- Entry points found with file:line
- Modules classified with evidence
- Mermaid C4Context diagram included
- Hotspot modules identified (for Deep mode follow-up)
```

## L2 Module Mapper

```
## TARGET
{target_path}

## OUTPUT
Write to: {outputs}/01-l2-modules.md

## DONE WHEN
- Import matrix with real counts
- Hotspots identified with evidence
- Coupling matrix completed
```

## Elegance Hunter

```
## TARGET
{target_path}

## OUTPUT
Write to: {outputs}/01-elegance.md

## DONE WHEN
- All antirez smells checked
- Every finding has file:line + grep evidence
- Hotspots table included
```

---

# Global Verifier Prompts

## L1 Verifier

```
## TARGET AGENT
l1-system-mapper

## FINDINGS TO VERIFY
{l1_output}

## OUTPUT
Write to: {outputs}/02-l1-verified.md

## DONE WHEN
- Every entry point claim verified
- Every module classification checked
- Verdict for each claim: Confirmed/Rejected/Modified
```

## L2 Verifier

```
## TARGET AGENT
l2-module-mapper

## FINDINGS TO VERIFY
{l2_output}

## OUTPUT
Write to: {outputs}/02-l2-verified.md

## DONE WHEN
- Every import count independently verified
- Coupling matrix values confirmed
- Hotspot claims checked
```

## Elegance Verifier

```
## TARGET AGENT
elegance-hunter

## FINDINGS TO VERIFY
{elegance_output}

## OUTPUT
Write to: {outputs}/02-elegance-verified.md

## DONE WHEN
- Every antirez violation independently verified
- Re-read actual code at each file:line
- Reject any finding without solid evidence
```
