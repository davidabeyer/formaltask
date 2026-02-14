# Module Investigator Task Prompts

## Module Deep Investigator

```
## SYSTEM CONTEXT (READ FIRST)
{synthesis}

## YOUR MODULE
{module_path}/{module}/

## OUTPUT
Write to: {outputs}/04-module-{module}.md

## DONE WHEN
- L2 internal coupling matrix
- L3 component structure with Mermaid
- L4 call graph for hotspot files
- Module-scoped elegance findings
- All claims have file:line evidence
```

## Module Investigator Verifier

```
## INVESTIGATOR FINDINGS TO VERIFY
{module_findings}

## MODULE PATH
{module_path}/{module}/

## OUTPUT
Write to: {outputs}/05-module-{module}-verified.md

## DONE WHEN
- Every import count re-verified
- Every elegance finding checked
- Hunt for MISSED violations
- Verdict for each claim: Confirmed/Rejected/Modified/Missed
```
