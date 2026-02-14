---
consumes: [target-content, target-type]
produces: [auditor-findings]
---

# Phase 3: Spawn Auditors

**quick:** Skip subagents. Critique the plan/specs yourself using auggie + warpgrep. Check for: over-engineering, missing dependencies, untestable criteria, blast radius concerns. Report findings inline.

**full:** **ALL in SINGLE message. No exceptions.**

**PLAN auditors:**

| Auditor | Model | Output | Skip if |
|---------|-------|--------|---------|
| `plan-skeptic` | sonnet | `skeptic.md` | `--skip-skeptic` |
| `blast-radius-analyzer` | sonnet | `blast-radius.md` | never |

**SPECS auditors:**

| Auditor | Model | Output | Territory |
|---------|-------|--------|-----------|
| `spec-decomposition-auditor` | sonnet | `decomposition.md` | Sizing, risk, API reality, antirez |
| `spec-dependency-auditor` | sonnet | `dependencies.md` | Hidden deps, graph connectivity, test coverage |
| `acceptance-criteria-auditor` | sonnet | `acceptance.md` | AC testability |
| `blast-radius-analyzer` | sonnet | `touchpoint-verification.md` | Import chains, conflict zones |

**Include in ALL SPECS agent prompts** (agents are isolated — they need format context):

```python
SPEC_FORMAT_CONTEXT = """
## Spec Format Reference
Each spec is YAML with fields:
- **title**: Task title
- **summary**: One paragraph description
- **depends_on**: Task numbers or empty list
- **implements**: Plan goal IDs this task addresses
- **context**: Why this exists
- **implementation**: Numbered steps with file paths and changes
- **acceptance_criteria**: Concrete commands that exit 0/1
- **required_reviews**: List of review types
- **testing**: unit/integration/e2e test descriptions
"""
```

**Additional SPECS spawns:**

```python
# Verify spec touchpoint claims match codebase reality
Task(subagent_type="blast-radius-analyzer",
     prompt=f"""Read specs in {spec_dir}. For EACH spec's "files to modify":
     1. Verify the files exist at claimed paths
     2. Verify claimed exports/functions are real
     3. Flag specs that CLAIM to touch file X but actually need file Y
     Output: touchpoint-verification.md with VALID/INVALID per spec""")
```

All write to `{run.outputs}/`. All run with `run_in_background=True`.

Wait for all auditors to complete before proceeding. If any auditor hasn't completed after 8 minutes, proceed with partial results.

**EXIT CRITERIA:** All auditors completed OR 8-minute timeout reached.
